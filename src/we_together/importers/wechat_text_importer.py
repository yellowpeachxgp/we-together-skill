"""微信文本记录 importer 原型。

支持最简 CSV/TSV 格式，兼容 WeChatMsg / 留痕等工具的导出：
  time, sender, content [, type]

产出：
  - raw_evidences（每条消息一行）
  - identity_candidates（每个 unique sender 一条）
  - event_candidates（每条消息一条，event_type=wechat_message）
  - relation_clues（相邻不同 sender 之间推一条弱关系）
  - group_clues（若 chat_name 以 "group" / "群" 等标记）

注意：这是 Phase 7 原型，不直接连微信抓取 SDK；真实抓取由上游工具完成后导出 CSV。
"""
from __future__ import annotations

import csv
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.candidate_store import (
    write_event_candidate,
    write_group_clue,
    write_identity_candidate,
    write_relation_clue,
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _create_import_job(conn: sqlite3.Connection, source_name: str) -> str:
    job_id = f"job_wx_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO import_jobs(
            import_job_id, source_type, source_platform, status, stats_json,
            started_at, finished_at
        ) VALUES(?, 'text_chat', 'wechat', 'completed', '{}', ?, ?)
        """,
        (job_id, _now(), _now()),
    )
    return job_id


def _create_evidence(conn: sqlite3.Connection, job_id: str, text: str,
                     locator: str, timestamp: str | None) -> str:
    eid = f"evd_wx_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO raw_evidences(
            evidence_id, import_job_id, source_type, source_platform, source_locator,
            content_type, normalized_text, timestamp, created_at
        ) VALUES(?, ?, 'text_chat', 'wechat', ?, 'text', ?, ?, ?)
        """,
        (eid, job_id, locator, text, timestamp, _now()),
    )
    return eid


def _looks_like_group(chat_name: str | None) -> bool:
    if not chat_name:
        return False
    lower = chat_name.lower()
    return (
        "group" in lower
        or "群" in chat_name
        or "团队" in chat_name
        or "频道" in chat_name
    )


def import_wechat_text(
    db_path: Path,
    *,
    csv_path: Path,
    chat_name: str | None = None,
) -> dict:
    """从 CSV 导入。CSV 至少包含列：time, sender, content。"""
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))

    conn = connect(db_path)
    job_id = _create_import_job(conn, csv_path.name)
    conn.commit()
    conn.close()

    sender_to_cid: dict[str, str] = {}
    messages: list[dict] = []

    with csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            sender = (row.get("sender") or "").strip()
            content = (row.get("content") or "").strip()
            ts = (row.get("time") or "").strip() or None
            if not sender or not content:
                continue
            conn = connect(db_path)
            ev = _create_evidence(
                conn, job_id, content,
                f"{csv_path.name}#L{i+2}",
                ts,
            )
            conn.commit()
            conn.close()

            # 每个 sender 写一次 identity_candidate
            if sender not in sender_to_cid:
                cid = write_identity_candidate(
                    db_path=db_path,
                    evidence_id=ev,
                    platform="wechat",
                    external_id=f"wx:{chat_name or 'unknown'}:{sender}",
                    display_name=sender,
                    confidence=0.7,
                    import_job_id=job_id,
                )
                sender_to_cid[sender] = cid

            evc = write_event_candidate(
                db_path=db_path,
                evidence_id=ev,
                event_type="wechat_message",
                actor_candidate_ids=[sender_to_cid[sender]],
                summary=content[:200],
                time_hint=ts,
                confidence=0.8,
                import_job_id=job_id,
            )
            messages.append({
                "sender": sender,
                "content": content,
                "evidence_id": ev,
                "event_candidate_id": evc,
            })

    # 相邻不同 sender → relation_clue
    pair_counts: dict[tuple[str, str], int] = {}
    for a, b in zip(messages, messages[1:]):
        if a["sender"] == b["sender"]:
            continue
        key = tuple(sorted([a["sender"], b["sender"]]))
        pair_counts[key] = pair_counts.get(key, 0) + 1

    relation_clues_written = 0
    for (s1, s2), count in pair_counts.items():
        if s1 not in sender_to_cid or s2 not in sender_to_cid:
            continue
        # 同一证据聚合：使用最后一条消息的 evidence_id 作为参考
        write_relation_clue(
            db_path=db_path,
            evidence_id=messages[-1]["evidence_id"],
            participant_candidate_ids=[sender_to_cid[s1], sender_to_cid[s2]],
            core_type_hint="acquaintance" if _looks_like_group(chat_name) else "friendship",
            strength_hint=min(1.0, 0.3 + 0.05 * count),
            summary=f"wechat 对话次数: {count}",
            confidence=min(0.85, 0.4 + 0.04 * count),
            import_job_id=job_id,
        )
        relation_clues_written += 1

    # 群场景 → group_clue
    group_clue_id = None
    if _looks_like_group(chat_name) and len(sender_to_cid) >= 3:
        group_clue_id = write_group_clue(
            db_path=db_path,
            evidence_id=messages[-1]["evidence_id"] if messages else "",
            group_type_hint="social_group",
            group_name_hint=chat_name,
            member_candidate_ids=list(sender_to_cid.values()),
            confidence=0.7,
            import_job_id=job_id,
        )

    return {
        "job_id": job_id,
        "messages": len(messages),
        "senders": len(sender_to_cid),
        "relation_clues": relation_clues_written,
        "group_clue_id": group_clue_id,
    }
