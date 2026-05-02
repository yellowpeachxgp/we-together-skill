"""自激活（Self-activation）服务 — 神经单元网格雏形。

在没有 user input 的时刻，也允许图谱自我演化：
  - 从当前 scene 的 activation_map 选一批活跃/潜在人物
  - 为每个人生成 self_reflection_event（内心独白 / 自主行动意图）
  - 受 daily_budget 限制，避免无界自激活

这为 Phase 7 的"无外部输入即可演化"提供最小雏形。
真实质量取决于后续配合 LLM 的推理深度，当前 stub 使用固定模板。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm.client import LLMClient, LLMMessage
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


DEFAULT_DAILY_BUDGET = 3
DEFAULT_PAIR_DAILY_BUDGET = 2


def _now() -> datetime:
    return datetime.now(UTC)


def _count_today_self_events(conn: sqlite3.Connection) -> int:
    start = (_now() - timedelta(hours=24)).isoformat()
    row = conn.execute(
        """
        SELECT COUNT(*) FROM events
        WHERE event_type = 'self_reflection_event'
        AND created_at >= ?
        """,
        (start,),
    ).fetchone()
    return row[0] or 0


def _default_reflection(display_name: str, scene_summary: str) -> str:
    return f"{display_name} 安静地思考：{scene_summary}"


def _llm_reflection(
    llm_client: LLMClient,
    *,
    display_name: str,
    persona: str | None,
    scene_summary: str,
) -> str:
    messages = [
        LLMMessage(
            role="system",
            content=(
                "你扮演一个角色，为其生成一段一两句的内心独白。"
                "严格保持角色人设，不要输出解释或 meta 信息。"
            ),
        ),
        LLMMessage(
            role="user",
            content=(
                f"角色: {display_name}\n"
                f"人设: {persona or '未知'}\n"
                f"当前场景: {scene_summary}\n"
                "请输出这位角色此刻的内心独白。"
            ),
        ),
    ]
    return llm_client.chat(messages).content.strip()


def self_activate(
    db_path: Path,
    *,
    scene_id: str,
    llm_client: LLMClient | None = None,
    daily_budget: int = DEFAULT_DAILY_BUDGET,
    per_run_limit: int = 2,
    derive_memories: bool = True,
) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    scene = conn.execute(
        "SELECT scene_id, scene_summary FROM scenes WHERE scene_id = ?", (scene_id,)
    ).fetchone()
    if scene is None:
        conn.close()
        raise ValueError(f"Scene not found: {scene_id}")

    used_today = _count_today_self_events(conn)
    remaining_budget = max(0, daily_budget - used_today)
    if remaining_budget == 0:
        conn.close()
        return {"created_count": 0, "reason": "daily_budget_exhausted"}

    # 选显式/潜伏激活的参与者
    participant_rows = conn.execute(
        """
        SELECT sp.person_id, p.primary_name, p.persona_summary, sp.activation_state,
               sp.activation_score
        FROM scene_participants sp
        JOIN persons p ON p.person_id = sp.person_id
        WHERE sp.scene_id = ?
        ORDER BY sp.activation_score DESC
        """,
        (scene_id,),
    ).fetchall()

    candidates = [
        row for row in participant_rows
        if row["activation_state"] in ("explicit", "latent")
    ][: min(per_run_limit, remaining_budget)]

    scene_summary = scene["scene_summary"] or "unknown scene"

    # 先算出每个 candidate 的 reflection 文本，不在 conn 打开时调 LLM
    prepared: list[dict] = []
    for row in candidates:
        display_name = row["primary_name"]
        if llm_client is not None:
            try:
                reflection = _llm_reflection(
                    llm_client,
                    display_name=display_name,
                    persona=row["persona_summary"],
                    scene_summary=scene_summary,
                )
            except Exception:
                reflection = _default_reflection(display_name, scene_summary)
        else:
            reflection = _default_reflection(display_name, scene_summary)
        prepared.append({
            "person_id": row["person_id"],
            "reflection": reflection,
        })

    # 所有事件写完再 commit，避免与后续 patch_applier 嵌套 connect 冲突
    created_ids: list[str] = []
    derived_memories: list[tuple[str, str, str]] = []  # (event_id, memory_id, person_id, reflection)
    now_iso = _now().isoformat()

    for item in prepared:
        event_id = f"evt_self_{uuid.uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO events(
                event_id, event_type, source_type, scene_id, timestamp, summary,
                visibility_level, confidence, is_structured,
                raw_evidence_refs_json, metadata_json, created_at
            ) VALUES(?, 'self_reflection_event', 'self_activation', ?, ?, ?,
                     'visible', 0.6, 1, '[]', ?, ?)
            """,
            (
                event_id, scene_id, now_iso, item["reflection"],
                json.dumps({"kind": "self_reflection", "actor": item["person_id"]},
                            ensure_ascii=False),
                now_iso,
            ),
        )
        conn.execute(
            """
            INSERT INTO event_participants(event_id, person_id, participant_role)
            VALUES(?, ?, 'actor')
            """,
            (event_id, item["person_id"]),
        )
        conn.execute(
            """
            INSERT INTO event_targets(event_id, target_type, target_id, impact_hint)
            VALUES(?, 'scene', ?, 'self reflection')
            """,
            (event_id, scene_id),
        )
        created_ids.append(event_id)
        if derive_memories:
            mem_id = f"mem_self_{uuid.uuid4().hex[:12]}"
            derived_memories.append((event_id, mem_id, item["person_id"], item["reflection"]))

    conn.commit()
    conn.close()

    # conn 已关闭；现在安全地调 patch_applier
    for event_id, mem_id, person_id, reflection in derived_memories:
        apply_patch_record(
            db_path=db_path,
            patch=build_patch(
                source_event_id=event_id,
                target_type="memory",
                target_id=mem_id,
                operation="create_memory",
                payload={
                    "memory_id": mem_id,
                    "memory_type": "individual_memory",
                    "summary": reflection,
                    "relevance_score": 0.5,
                    "confidence": 0.6,
                    "is_shared": 0,
                    "status": "active",
                    "metadata_json": {
                        "source": "self_activation",
                        "actor_person_id": person_id,
                        "scene_id": scene_id,
                    },
                },
                confidence=0.6,
                reason="memory derived from self-reflection",
            ),
        )
        owner_conn = connect(db_path)
        owner_conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) VALUES(?, 'person', ?, 'self')",
            (mem_id, person_id),
        )
        owner_conn.commit()
        owner_conn.close()

    return {
        "created_count": len(created_ids),
        "event_ids": created_ids,
        "remaining_budget": remaining_budget - len(created_ids),
        "reason": "ok",
    }


def _count_today_pair_events(conn: sqlite3.Connection) -> int:
    start = (_now() - timedelta(hours=24)).isoformat()
    row = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_type = 'latent_interaction_event' "
        "AND created_at >= ?",
        (start,),
    ).fetchone()
    return row[0] or 0


def self_activate_pair_interactions(
    db_path: Path,
    *,
    scene_id: str,
    llm_client: LLMClient | None = None,
    daily_budget: int = DEFAULT_PAIR_DAILY_BUDGET,
    per_run_limit: int = 1,
    min_activation_score: float = 0.3,
) -> dict:
    """在当前 scene 活跃 persons 中挑 pair，生成 latent_interaction_event。

    返回: {"created_count", "event_ids", "remaining_budget", "reason"}
    """
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    scene = conn.execute(
        "SELECT scene_id, scene_summary FROM scenes WHERE scene_id = ? AND status = 'active'",
        (scene_id,),
    ).fetchone()
    if scene is None:
        conn.close()
        raise ValueError(f"Scene not found or not active: {scene_id}")

    used = _count_today_pair_events(conn)
    remaining = max(0, daily_budget - used)
    if remaining == 0:
        conn.close()
        return {"created_count": 0, "reason": "daily_budget_exhausted"}

    rows = conn.execute(
        """
        SELECT sp.person_id, p.primary_name, sp.activation_score
        FROM scene_participants sp
        JOIN persons p ON p.person_id = sp.person_id
        WHERE sp.scene_id = ?
          AND sp.activation_state IN ('explicit', 'latent')
          AND (sp.activation_score IS NULL OR sp.activation_score >= ?)
        ORDER BY sp.activation_score DESC
        """,
        (scene_id, min_activation_score),
    ).fetchall()

    if len(rows) < 2:
        conn.close()
        return {"created_count": 0, "reason": "not_enough_active_persons"}

    # pair top-2..top-N
    pairs: list[tuple[sqlite3.Row, sqlite3.Row]] = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            pairs.append((rows[i], rows[j]))
            if len(pairs) >= min(per_run_limit, remaining):
                break
        if len(pairs) >= min(per_run_limit, remaining):
            break

    scene_summary = scene["scene_summary"] or "unknown scene"
    now_iso = _now().isoformat()
    created: list[str] = []
    derived_memories: list[tuple[str, str, str, str, str]] = []

    for a, b in pairs:
        summary = f"{a['primary_name']} 与 {b['primary_name']} 在 {scene_summary} 中自发互动"
        if llm_client is not None:
            try:
                payload = llm_client.chat_json(
                    [
                        LLMMessage(role="system", content="你是人物自发交互生成器。"),
                        LLMMessage(
                            role="user",
                            content=(
                                f"{a['primary_name']} 和 {b['primary_name']} 在 '{scene_summary}' "
                                "中会自发地聊些什么？输出 JSON: {\"summary\": \"一句话\"}"
                            ),
                        ),
                    ],
                    schema_hint={"summary": "str"},
                )
                if payload.get("summary"):
                    summary = str(payload["summary"]).strip()
            except Exception:
                pass

        event_id = f"evt_pair_{uuid.uuid4().hex[:12]}"
        conn.execute(
            """INSERT INTO events(event_id, event_type, source_type, scene_id, timestamp,
               summary, visibility_level, confidence, is_structured,
               raw_evidence_refs_json, metadata_json, created_at)
               VALUES(?, 'latent_interaction_event', 'self_activation', ?, ?, ?,
                      'visible', 0.55, 1, '[]', ?, ?)""",
            (event_id, scene_id, now_iso, summary,
             json.dumps({"kind": "latent_interaction", "actors": [a["person_id"], b["person_id"]]},
                        ensure_ascii=False),
             now_iso),
        )
        for p in (a, b):
            conn.execute(
                "INSERT INTO event_participants(event_id, person_id, participant_role) "
                "VALUES(?, ?, 'actor')",
                (event_id, p["person_id"]),
            )
        conn.execute(
            "INSERT INTO event_targets(event_id, target_type, target_id, impact_hint) "
            "VALUES(?, 'scene', ?, 'latent interaction')",
            (event_id, scene_id),
        )
        created.append(event_id)
        mem_id = f"mem_pair_{uuid.uuid4().hex[:12]}"
        derived_memories.append((event_id, mem_id, a["person_id"], b["person_id"], summary))

    conn.commit()
    conn.close()

    for event_id, mem_id, pid_a, pid_b, summary in derived_memories:
        apply_patch_record(
            db_path=db_path,
            patch=build_patch(
                source_event_id=event_id,
                target_type="memory",
                target_id=mem_id,
                operation="create_memory",
                payload={
                    "memory_id": mem_id,
                    "memory_type": "shared_memory",
                    "summary": summary,
                    "relevance_score": 0.55,
                    "confidence": 0.55,
                    "is_shared": 1,
                    "status": "active",
                    "metadata_json": {
                        "source": "latent_interaction",
                        "actors": [pid_a, pid_b],
                        "scene_id": scene_id,
                    },
                },
                confidence=0.55,
                reason="memory derived from latent interaction",
            ),
        )
        owner_conn = connect(db_path)
        for pid in (pid_a, pid_b):
            owner_conn.execute(
                "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
                "VALUES(?, 'person', ?, 'pair')",
                (mem_id, pid),
            )
        owner_conn.commit()
        owner_conn.close()

    return {
        "created_count": len(created),
        "event_ids": created,
        "remaining_budget": remaining - len(created),
        "reason": "ok",
    }
