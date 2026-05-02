"""graph_clock（Phase 45 GT）：图谱内部时钟。

不变式 #24：时间敏感服务必须读 graph_clock.now() 优先，datetime.now() 仅限内核。

语义：
- now(db) → 优先 simulated_now；未设或 NULL → datetime.now(UTC)
- set(db, ts) 设置模拟时间
- advance(db, days=N) 推进 N 天
- freeze(db) / unfreeze(db) 冻结/解冻（冻结后 now 不随真实时间漂移）
- fallback: 若 graph_clock 表不存在（旧 migration 未跑），自动用 datetime.now(UTC)
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _has_clock_table(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name='graph_clock'"
    ).fetchone()
    return row is not None


def now(db_path: Path | None = None) -> datetime:
    if db_path is None:
        return datetime.now(UTC)
    try:
        conn = sqlite3.connect(db_path)
    except Exception:
        return datetime.now(UTC)
    try:
        if not _has_clock_table(conn):
            return datetime.now(UTC)
        row = conn.execute(
            "SELECT simulated_now, frozen FROM graph_clock WHERE id=1"
        ).fetchone()
        if not row:
            return datetime.now(UTC)
        simulated, frozen = row
        parsed = _parse_iso(simulated)
        if parsed is None:
            return datetime.now(UTC)
        if frozen:
            return parsed
        # 非冻结：以 simulated_now 为基准，推进到真实流逝
        last_update_row = conn.execute(
            "SELECT updated_at FROM graph_clock WHERE id=1"
        ).fetchone()
        last_update = _parse_iso(last_update_row[0]) if last_update_row else None
        if last_update is None:
            return parsed
        elapsed = datetime.now(UTC) - last_update.replace(tzinfo=UTC)
        return parsed + elapsed
    finally:
        conn.close()


def set_time(db_path: Path, ts: datetime | str) -> dict:
    if isinstance(ts, datetime):
        value = ts.astimezone(UTC).isoformat()
    else:
        value = ts
    conn = sqlite3.connect(db_path)
    try:
        if not _has_clock_table(conn):
            raise RuntimeError("graph_clock table missing; run migration 0017")
        before = conn.execute(
            "SELECT simulated_now FROM graph_clock WHERE id=1"
        ).fetchone()
        conn.execute(
            "UPDATE graph_clock SET simulated_now=?, updated_at=datetime('now') "
            "WHERE id=1", (value,),
        )
        conn.execute(
            "INSERT INTO graph_clock_history(action, before_value, after_value, recorded_at) "
            "VALUES('set', ?, ?, datetime('now'))",
            (before[0] if before else None, value),
        )
        conn.commit()
        return {"simulated_now": value}
    finally:
        conn.close()


def advance(db_path: Path, *, days: int = 0, hours: int = 0, seconds: int = 0) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        if not _has_clock_table(conn):
            raise RuntimeError("graph_clock table missing; run migration 0017")
        row = conn.execute(
            "SELECT simulated_now FROM graph_clock WHERE id=1"
        ).fetchone()
        base_str = row[0] if row else None
        base = _parse_iso(base_str) or datetime.now(UTC)
        new_ts = base + timedelta(days=days, hours=hours, seconds=seconds)
        value = new_ts.astimezone(UTC).isoformat()
        conn.execute(
            "UPDATE graph_clock SET simulated_now=?, updated_at=datetime('now') "
            "WHERE id=1", (value,),
        )
        conn.execute(
            "INSERT INTO graph_clock_history(action, before_value, after_value, recorded_at) "
            "VALUES('advance', ?, ?, datetime('now'))",
            (base_str, value),
        )
        conn.commit()
        return {"simulated_now": value, "advanced_days": days}
    finally:
        conn.close()


def freeze(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        if not _has_clock_table(conn):
            raise RuntimeError("graph_clock table missing; run migration 0017")
        conn.execute(
            "UPDATE graph_clock SET frozen=1, updated_at=datetime('now') WHERE id=1"
        )
        conn.execute(
            "INSERT INTO graph_clock_history(action, before_value, after_value, recorded_at) "
            "VALUES('freeze', NULL, NULL, datetime('now'))"
        )
        conn.commit()
        return {"frozen": True}
    finally:
        conn.close()


def unfreeze(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        if not _has_clock_table(conn):
            raise RuntimeError("graph_clock table missing; run migration 0017")
        conn.execute(
            "UPDATE graph_clock SET frozen=0, updated_at=datetime('now') WHERE id=1"
        )
        conn.execute(
            "INSERT INTO graph_clock_history(action, before_value, after_value, recorded_at) "
            "VALUES('unfreeze', NULL, NULL, datetime('now'))"
        )
        conn.commit()
        return {"frozen": False}
    finally:
        conn.close()


def clear(db_path: Path) -> dict:
    """清除模拟时间，回落到真实时间。"""
    conn = sqlite3.connect(db_path)
    try:
        if not _has_clock_table(conn):
            raise RuntimeError("graph_clock table missing; run migration 0017")
        conn.execute(
            "UPDATE graph_clock SET simulated_now=NULL, frozen=0, "
            "updated_at=datetime('now') WHERE id=1"
        )
        conn.execute(
            "INSERT INTO graph_clock_history(action, before_value, after_value, recorded_at) "
            "VALUES('clear', NULL, NULL, datetime('now'))"
        )
        conn.commit()
        return {"cleared": True}
    finally:
        conn.close()
