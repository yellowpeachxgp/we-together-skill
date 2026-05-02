"""tick_sanity（Phase 34 EV-9/10）：评估 simulate 一段时间后的图谱合理性。

指标：
- growth_rate：memory / event 增长速率
- anomalies：confidence 突变、孤立 memory、重复事件
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def check_growth(
    db_path: Path, *,
    ticks: int, max_memory_per_tick: float = 5.0, max_event_per_tick: float = 20.0,
) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        mem = conn.execute("SELECT COUNT(*) FROM memories WHERE status='active'").fetchone()[0]
        ev = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    finally:
        conn.close()
    ok_mem = ticks == 0 or (mem / max(ticks, 1)) <= max_memory_per_tick * 10
    ok_ev = ticks == 0 or (ev / max(ticks, 1)) <= max_event_per_tick * 10
    return {
        "memory_count": mem,
        "event_count": ev,
        "memory_per_tick": mem / max(ticks, 1),
        "event_per_tick": ev / max(ticks, 1),
        "memory_growth_ok": ok_mem,
        "event_growth_ok": ok_ev,
    }


def check_anomalies(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        low_conf = conn.execute(
            "SELECT COUNT(*) FROM memories WHERE confidence < 0.1 AND status='active'",
        ).fetchone()[0]
        orphans = conn.execute(
            "SELECT COUNT(*) FROM memories m WHERE status='active' AND NOT EXISTS "
            "(SELECT 1 FROM memory_owners WHERE memory_id=m.memory_id)",
        ).fetchone()[0]
        dup_events = conn.execute(
            "SELECT COUNT(*) FROM (SELECT summary, COUNT(*) c FROM events "
            "GROUP BY summary HAVING c > 1)",
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "low_confidence_memories": low_conf,
        "orphan_memories": orphans,
        "duplicate_event_summaries": dup_events,
        "anomaly_count": int(low_conf + orphans + dup_events),
    }


def evaluate(db_path: Path, *, ticks: int) -> dict:
    growth = check_growth(db_path, ticks=ticks)
    anomalies = check_anomalies(db_path)
    healthy = (
        growth["memory_growth_ok"]
        and growth["event_growth_ok"]
        and anomalies["anomaly_count"] < 10
    )
    return {"growth": growth, "anomalies": anomalies, "healthy": healthy}
