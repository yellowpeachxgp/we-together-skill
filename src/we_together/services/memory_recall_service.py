"""TL-5 Memory Recall Event：Phase 8 self_activation 的"纪念日回忆"扩展。

触发规则：
  - 某条高 relevance_score memory 的 created_at 距今 = N 天整数倍（anniversary）
  - 生成一条 memory_recall_event + 简短回忆文本
  - 受 DEFAULT_RECALL_DAILY_BUDGET 约束
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect

DEFAULT_RECALL_DAILY_BUDGET = 2
DEFAULT_ANNIVERSARY_DAYS = {30, 90, 180, 365}
MIN_RELEVANCE_FOR_RECALL = 0.6


def _count_today_recall(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_type = 'memory_recall_event' "
        "AND date(created_at) = date('now')"
    ).fetchone()
    return row[0] or 0


def recall_anniversary_memories(
    db_path: Path,
    *,
    daily_budget: int = DEFAULT_RECALL_DAILY_BUDGET,
    anniversary_days: set[int] | None = None,
) -> dict:
    days = anniversary_days or DEFAULT_ANNIVERSARY_DAYS
    now = datetime.now(UTC)
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row

    used = _count_today_recall(conn)
    remaining = max(0, daily_budget - used)
    if remaining == 0:
        conn.close()
        return {"recalled_count": 0, "reason": "daily_budget_exhausted"}

    # 找 high-relevance memory
    rows = conn.execute(
        """SELECT memory_id, summary, created_at, relevance_score
           FROM memories
           WHERE status = 'active' AND relevance_score >= ?
           ORDER BY created_at DESC""",
        (MIN_RELEVANCE_FOR_RECALL,),
    ).fetchall()

    created: list[dict] = []
    for r in rows:
        if remaining == 0:
            break
        try:
            created_at = datetime.fromisoformat(r["created_at"])
        except (TypeError, ValueError):
            continue
        age_days = (now - created_at).days
        if age_days in days:
            eid = f"evt_recall_{uuid.uuid4().hex[:10]}"
            summary = f"回忆起 {age_days} 天前：{r['summary']}"
            conn.execute(
                """INSERT INTO events(event_id, event_type, source_type, timestamp,
                   summary, visibility_level, confidence, is_structured,
                   raw_evidence_refs_json, metadata_json, created_at)
                   VALUES(?, 'memory_recall_event', 'self_activation',
                          datetime('now'), ?, 'visible', 0.6, 1, '[]', ?,
                          datetime('now'))""",
                (eid, summary,
                 json.dumps({"recalled_memory_id": r["memory_id"],
                             "age_days": age_days}, ensure_ascii=False)),
            )
            conn.execute(
                "INSERT INTO event_targets(event_id, target_type, target_id, impact_hint) "
                "VALUES(?, 'memory', ?, 'recall')",
                (eid, r["memory_id"]),
            )
            created.append({"event_id": eid, "memory_id": r["memory_id"],
                            "age_days": age_days})
            remaining -= 1
    conn.commit()
    conn.close()
    return {"recalled_count": len(created), "events": created,
            "remaining_budget": remaining}
