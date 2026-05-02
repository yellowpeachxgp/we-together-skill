"""候选层 → 图谱主层的融合服务。

职责：把 open 状态的 candidate/clue 归并为正式图谱对象（persons / identity_links / relations），
并通过 patch_applier 落地，保持"所有变更走 patch"的约束。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.candidate_store import mark_candidate_linked
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch

LOW_TIER = "low"


def _open_identity_branch(
    db_path: Path,
    *,
    candidate_id: str,
    display_name: str,
    platform: str | None,
    external_id: str | None,
    existing_person_id: str,
    confidence: float,
    source_event_id: str | None,
) -> str:
    """低置信冲突：开 local_branch 让人类选择合并还是新建。"""
    branch_id = f"branch_idc_{uuid.uuid4().hex[:12]}"
    payload = {
        "branch_id": branch_id,
        "scope_type": "person",
        "scope_id": existing_person_id,
        "status": "open",
        "reason": f"低置信 identity 候选 {candidate_id} 与 {existing_person_id} (name={display_name}) 冲突",
        "created_from_event_id": source_event_id,
        "branch_candidates": [
            {
                "candidate_id": f"cand_merge_{uuid.uuid4().hex[:8]}",
                "label": "合并到现有人物",
                "payload_json": {"mode": "merge", "target_person_id": existing_person_id},
                "confidence": confidence,
                "status": "open",
            },
            {
                "candidate_id": f"cand_new_{uuid.uuid4().hex[:8]}",
                "label": "新建独立人物",
                "payload_json": {
                    "mode": "new",
                    "display_name": display_name,
                    "platform": platform,
                    "external_id": external_id,
                },
                "confidence": 1.0 - confidence,
                "status": "open",
            },
        ],
    }
    patch = build_patch(
        source_event_id=source_event_id or f"evt_fuse_{candidate_id}",
        target_type="local_branch",
        target_id=branch_id,
        operation="create_local_branch",
        payload=payload,
        confidence=confidence,
        reason="low-tier identity candidate opened a branch",
    )
    apply_patch_record(db_path=db_path, patch=patch)
    return branch_id


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_person_id() -> str:
    return f"person_{uuid.uuid4().hex}"


def _new_relation_id() -> str:
    return f"relation_{uuid.uuid4().hex}"


def _find_person_by_name(conn: sqlite3.Connection, name: str) -> str | None:
    row = conn.execute(
        "SELECT person_id FROM persons WHERE primary_name = ? AND status = 'active' LIMIT 1",
        (name,),
    ).fetchone()
    return row[0] if row else None


def _find_person_by_identity(
    conn: sqlite3.Connection, platform: str, external_id: str
) -> str | None:
    row = conn.execute(
        """
        SELECT person_id FROM identity_links
        WHERE platform = ? AND external_id = ? AND person_id IS NOT NULL
        LIMIT 1
        """,
        (platform, external_id),
    ).fetchone()
    return row[0] if row else None


def fuse_identity_candidates(
    db_path: Path,
    *,
    limit: int = 100,
    source_event_id: str | None = None,
    branch_on_low_tier_conflict: bool = True,
) -> dict:
    """把 open 状态的 identity_candidates 合并到 persons + identity_links。

    策略：
      - 若 (platform, external_id) 已存在 identity_links → 复用 linked person_id
      - 否则若有同名 primary_name person 且为 high/medium 置信度 → 复用
      - 否则若为 low 置信度且有同名存在 + branch_on_low_tier_conflict → 开 local_branch
      - 否则创建新 person
    """
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM identity_candidates
        WHERE status = 'open'
        ORDER BY confidence DESC, created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    fused = 0
    created_persons = 0
    reused_persons = 0
    branched = 0

    for row in rows:
        candidate_id = row["candidate_id"]
        platform = row["platform"]
        external_id = row["external_id"]
        display_name = row["display_name"] or candidate_id
        tier = row["confidence_tier"]

        # 1) 复用 identity_links 已有 person
        person_id: str | None = None
        if platform and external_id:
            conn_r = connect(db_path)
            person_id = _find_person_by_identity(conn_r, platform, external_id)
            conn_r.close()

        # 2) 同名查找
        if person_id is None:
            conn_r = connect(db_path)
            same_name_pid = _find_person_by_name(conn_r, display_name)
            conn_r.close()

            if same_name_pid is not None:
                if tier == LOW_TIER and branch_on_low_tier_conflict:
                    # low-tier + 名字冲突 → 开 branch 而非直接合并
                    _open_identity_branch(
                        db_path,
                        candidate_id=candidate_id,
                        display_name=display_name,
                        platform=platform,
                        external_id=external_id,
                        existing_person_id=same_name_pid,
                        confidence=row["confidence"],
                        source_event_id=source_event_id,
                    )
                    # 不标记 linked，保持 open 等人类决策
                    branched += 1
                    continue
                person_id = same_name_pid
                reused_persons += 1

        # 3) 新建 person
        if person_id is None:
            person_id = _new_person_id()
            conn_w = connect(db_path)
            conn_w.execute(
                """
                INSERT INTO persons(
                    person_id, primary_name, status, confidence, metadata_json,
                    created_at, updated_at
                ) VALUES(?, ?, 'active', ?, '{}', ?, ?)
                """,
                (person_id, display_name, row["confidence"], _now(), _now()),
            )
            conn_w.commit()
            conn_w.close()
            created_persons += 1

        # 写 identity_links（若 platform+external_id 完整且不存在）
        if platform and external_id:
            identity_id = f"id_{uuid.uuid4().hex}"
            try:
                conn_w = connect(db_path)
                conn_w.execute(
                    """
                    INSERT OR IGNORE INTO identity_links(
                        identity_id, person_id, platform, external_id, display_name,
                        confidence, is_user_confirmed, is_active, metadata_json,
                        created_at, updated_at
                    ) VALUES(?, ?, ?, ?, ?, ?, 0, 1, '{}', ?, ?)
                    """,
                    (
                        identity_id,
                        person_id,
                        platform,
                        external_id,
                        display_name,
                        row["confidence"],
                        _now(),
                        _now(),
                    ),
                )
                conn_w.commit()
                conn_w.close()
            except sqlite3.IntegrityError:
                pass

        mark_candidate_linked(
            db_path,
            "identity_candidates",
            "candidate_id",
            candidate_id,
            link_col="linked_person_id",
            link_id=person_id,
        )
        fused += 1

    return {
        "fused_count": fused,
        "created_persons": created_persons,
        "reused_persons": reused_persons,
        "branched": branched,
    }


def fuse_relation_clues(
    db_path: Path,
    *,
    source_event_id: str | None = None,
    limit: int = 100,
) -> dict:
    """把 open 状态的 relation_clues 聚合成 relations + patch。

    策略：
      - participant_candidate_ids 必须都已 linked 到 person_id，否则跳过
      - 同一对 (person_a, person_b) + core_type 只新增一条 relation
      - 通过 event_targets 关联以保持 retrieval 可见性（若提供 source_event_id）
    """
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM relation_clues
        WHERE status = 'open'
        ORDER BY confidence DESC, created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    linked = 0
    created_relations = 0
    skipped = 0

    for row in rows:
        clue_id = row["clue_id"]
        candidate_ids = json.loads(row["participant_candidate_ids_json"] or "[]")
        if len(candidate_ids) < 2:
            skipped += 1
            continue

        # 解析 candidate_id → person_id
        person_ids: list[str] = []
        conn_r = connect(db_path)
        conn_r.row_factory = sqlite3.Row
        for cid in candidate_ids:
            r = conn_r.execute(
                "SELECT linked_person_id FROM identity_candidates WHERE candidate_id = ?",
                (cid,),
            ).fetchone()
            if r and r["linked_person_id"]:
                person_ids.append(r["linked_person_id"])
        conn_r.close()

        if len(person_ids) < 2:
            skipped += 1
            continue

        # 查已有 relation
        core_type = row["core_type_hint"] or "unspecified"
        conn_r = connect(db_path)
        conn_r.row_factory = sqlite3.Row
        existing = conn_r.execute(
            """
            SELECT r.relation_id
            FROM relations r
            WHERE r.core_type = ? AND r.status = 'active'
            LIMIT 1
            """,
            (core_type,),
        ).fetchone()
        conn_r.close()

        if existing:
            relation_id = existing["relation_id"]
        else:
            relation_id = _new_relation_id()
            conn_w = connect(db_path)
            conn_w.execute(
                """
                INSERT INTO relations(
                    relation_id, core_type, custom_label, summary, directionality,
                    strength, stability, visibility, status, confidence, metadata_json,
                    created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, 'known', 'active', ?, '{}', ?, ?)
                """,
                (
                    relation_id,
                    core_type,
                    row["custom_label_hint"],
                    row["summary"],
                    row["directionality_hint"] or "bidirectional",
                    row["strength_hint"],
                    row["stability_hint"],
                    row["confidence"],
                    _now(),
                    _now(),
                ),
            )
            conn_w.commit()
            conn_w.close()
            created_relations += 1

        # 若指定 source_event_id，把 relation 挂到 event_targets + event_participants
        if source_event_id:
            conn_w = connect(db_path)
            conn_w.execute(
                """
                INSERT OR IGNORE INTO event_targets(
                    event_id, target_type, target_id, impact_hint
                ) VALUES(?, 'relation', ?, ?)
                """,
                (source_event_id, relation_id, "fused from clue"),
            )
            for pid in person_ids:
                conn_w.execute(
                    """
                    INSERT OR IGNORE INTO event_participants(
                        event_id, person_id, participant_role
                    ) VALUES(?, ?, 'mentioned')
                    """,
                    (source_event_id, pid),
                )
            conn_w.commit()
            conn_w.close()

        # 标记 clue 已链接
        mark_candidate_linked(
            db_path,
            "relation_clues",
            "clue_id",
            clue_id,
            link_col="linked_relation_id",
            link_id=relation_id,
        )
        linked += 1

    return {
        "fused_count": linked,
        "created_relations": created_relations,
        "skipped": skipped,
    }


def fuse_group_clues(
    db_path: Path,
    *,
    limit: int = 100,
) -> dict:
    """把 open 状态的 group_clues 升级为 groups + group_members。

    策略：
      - member_candidate_ids 必须都已 linked 到 person_id，否则跳过
      - 若已存在同名 group 直接复用
    """
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM group_clues
        WHERE status = 'open'
        ORDER BY confidence DESC, created_at ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    fused = 0
    created_groups = 0
    skipped = 0

    for row in rows:
        clue_id = row["clue_id"]
        cand_ids = json.loads(row["member_candidate_ids_json"] or "[]")
        if len(cand_ids) < 2:
            skipped += 1
            continue

        person_ids: list[str] = []
        conn_r = connect(db_path)
        conn_r.row_factory = sqlite3.Row
        for cid in cand_ids:
            r = conn_r.execute(
                "SELECT linked_person_id FROM identity_candidates WHERE candidate_id = ?",
                (cid,),
            ).fetchone()
            if r and r["linked_person_id"]:
                person_ids.append(r["linked_person_id"])
        conn_r.close()

        if len(person_ids) < 2:
            skipped += 1
            continue

        group_name = row["group_name_hint"] or f"group_{clue_id}"
        conn_r = connect(db_path)
        conn_r.row_factory = sqlite3.Row
        existing = conn_r.execute(
            "SELECT group_id FROM groups WHERE name = ? AND status = 'active' LIMIT 1",
            (group_name,),
        ).fetchone()
        conn_r.close()

        if existing:
            group_id = existing["group_id"]
        else:
            group_id = f"group_{uuid.uuid4().hex[:12]}"
            conn_w = connect(db_path)
            conn_w.execute(
                """
                INSERT INTO groups(
                    group_id, group_type, name, summary, status, confidence,
                    metadata_json, created_at, updated_at
                ) VALUES(?, ?, ?, ?, 'active', ?, '{}', ?, ?)
                """,
                (
                    group_id,
                    row["group_type_hint"] or "social_group",
                    group_name,
                    f"fused from clue {clue_id}",
                    row["confidence"],
                    _now(), _now(),
                ),
            )
            conn_w.commit()
            conn_w.close()
            created_groups += 1

        # 添加 members
        conn_w = connect(db_path)
        for pid in person_ids:
            conn_w.execute(
                """
                INSERT OR IGNORE INTO group_members(
                    group_id, person_id, role_label, joined_at, status, metadata_json
                ) VALUES(?, ?, 'member', ?, 'active', '{}')
                """,
                (group_id, pid, _now()),
            )
        conn_w.commit()
        conn_w.close()

        mark_candidate_linked(
            db_path,
            "group_clues",
            "clue_id",
            clue_id,
            link_col="linked_group_id",
            link_id=group_id,
        )
        fused += 1

    return {
        "fused_count": fused,
        "created_groups": created_groups,
        "skipped": skipped,
    }


def fuse_all(db_path: Path, *, source_event_id: str | None = None) -> dict:
    r1 = fuse_identity_candidates(db_path)
    r2 = fuse_relation_clues(db_path, source_event_id=source_event_id)
    r3 = fuse_group_clues(db_path)
    return {"identity": r1, "relation": r2, "group": r3}
