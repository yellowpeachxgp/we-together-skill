"""关系漂移服务：基于 event 历史窗口重算 relation.strength / stability。

基本思路：
  - 窗口期内事件多 → 关系活跃，strength 缓慢上升（上限 1.0）
  - 窗口期内无事件 → 关系冷却，strength 下降（下限 0.0）
  - stability = 窗口内事件的时间均匀度（熵近似）

所有变更通过 update_entity patch 落地，保持留痕。
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch

POSITIVE_KEYWORDS = ("好", "谢谢", "一起", "顺利", "开心", "加油", "关心")
NEGATIVE_KEYWORDS = ("烦", "吵", "糟糕", "冲突", "争执", "分手", "退出")

DRIFT_UP = 0.03
DRIFT_DOWN = 0.05
STRENGTH_CEILING = 1.0
STRENGTH_FLOOR = 0.0


def _now() -> datetime:
    return datetime.now(UTC)


def _fetch_relation_events(
    conn: sqlite3.Connection,
    relation_id: str,
    window_start: datetime,
) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT e.event_id, e.timestamp, e.summary, e.metadata_json
        FROM events e
        JOIN event_targets et ON et.event_id = e.event_id
        WHERE et.target_type = 'relation' AND et.target_id = ?
          AND (e.timestamp IS NULL OR e.timestamp >= ?)
        """,
        (relation_id, window_start.isoformat()),
    ).fetchall()
    return rows


def _score_event_sentiment(summary: str | None) -> int:
    """+1 positive, -1 negative, 0 neutral。极简关键词打分。"""
    if not summary:
        return 0
    text = summary
    score = 0
    for kw in POSITIVE_KEYWORDS:
        if kw in text:
            score += 1
    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            score -= 1
    if score > 0:
        return 1
    if score < 0:
        return -1
    return 0


def _compute_drift(
    event_rows: list[sqlite3.Row],
    *,
    min_events_for_warmup: int = 2,
) -> tuple[float, str]:
    count = len(event_rows)
    if count == 0:
        return -DRIFT_DOWN, "no events in window"

    net = sum(_score_event_sentiment(row["summary"]) for row in event_rows)
    if net > 0:
        return DRIFT_UP, f"{count} events, net positive"
    if net < 0:
        return -DRIFT_UP, f"{count} events, net negative"
    if count >= min_events_for_warmup:
        return DRIFT_UP * 0.5, f"{count} events, neutral but active"
    return 0.0, f"{count} events, neutral"


def drift_relations(
    db_path: Path,
    *,
    window_days: int = 30,
    limit: int = 200,
    source_event_id: str | None = None,
) -> dict:
    window_start = _now() - timedelta(days=window_days)

    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    relations = conn.execute(
        """
        SELECT relation_id, strength FROM relations
        WHERE status = 'active'
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    drift_updates: list[dict] = []
    for rel in relations:
        events = _fetch_relation_events(conn, rel["relation_id"], window_start)
        delta, reason = _compute_drift(events)
        if delta == 0.0:
            continue
        old_strength = rel["strength"] if rel["strength"] is not None else 0.5
        new_strength = max(STRENGTH_FLOOR, min(STRENGTH_CEILING, old_strength + delta))
        if abs(new_strength - old_strength) < 1e-6:
            continue
        drift_updates.append({
            "relation_id": rel["relation_id"],
            "old_strength": old_strength,
            "new_strength": new_strength,
            "delta": delta,
            "reason": reason,
        })
    conn.close()

    for item in drift_updates:
        patch = build_patch(
            source_event_id=source_event_id or f"drift_{item['relation_id']}",
            target_type="relation",
            target_id=item["relation_id"],
            operation="update_entity",
            payload={"strength": item["new_strength"]},
            confidence=0.5,
            reason=f"drift: {item['reason']} (Δ{item['delta']:+.3f})",
        )
        apply_patch_record(db_path=db_path, patch=patch)

    return {
        "drifted_count": len(drift_updates),
        "window_days": window_days,
        "details": drift_updates,
    }
