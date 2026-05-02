"""Persona history 服务：记录 + 查询 persona_summary 的时序变化。"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect


def _now() -> str:
    return datetime.now(UTC).isoformat()


def record_persona_change(
    db_path: Path,
    *,
    person_id: str,
    persona_summary: str | None = None,
    style_summary: str | None = None,
    boundary_summary: str | None = None,
    source_reason: str | None = None,
    confidence: float | None = None,
) -> str:
    """写一条 persona_history 行，并把前一条的 valid_to 设为现在。"""
    now = _now()
    hid = f"ph_{uuid.uuid4().hex[:12]}"
    conn = connect(db_path)
    # close 上一条
    conn.execute(
        "UPDATE persona_history SET valid_to = ? "
        "WHERE person_id = ? AND valid_to IS NULL",
        (now, person_id),
    )
    conn.execute(
        """INSERT INTO persona_history(
            history_id, person_id, persona_summary, style_summary, boundary_summary,
            valid_from, valid_to, source_reason, confidence, created_at
        ) VALUES(?,?,?,?,?,?,NULL,?,?,?)""",
        (hid, person_id, persona_summary, style_summary, boundary_summary,
         now, source_reason, confidence, now),
    )
    conn.commit()
    conn.close()
    return hid


def query_history(db_path: Path, person_id: str) -> list[dict]:
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT history_id, persona_summary, style_summary, boundary_summary, "
        "valid_from, valid_to, source_reason, confidence "
        "FROM persona_history WHERE person_id = ? ORDER BY valid_from DESC",
        (person_id,),
    ).fetchall()
    conn.close()
    return [
        {"history_id": r[0], "persona_summary": r[1], "style_summary": r[2],
         "boundary_summary": r[3], "valid_from": r[4], "valid_to": r[5],
         "source_reason": r[6], "confidence": r[7]}
        for r in rows
    ]


def query_as_of(
    db_path: Path, person_id: str, as_of_iso: str,
) -> dict | None:
    """返回 valid_from <= as_of <= (valid_to or +inf) 的那行。"""
    conn = connect(db_path)
    row = conn.execute(
        "SELECT history_id, persona_summary, style_summary, boundary_summary, "
        "valid_from, valid_to "
        "FROM persona_history WHERE person_id = ? "
        "AND valid_from <= ? "
        "AND (valid_to IS NULL OR valid_to >= ?) "
        "ORDER BY valid_from DESC LIMIT 1",
        (person_id, as_of_iso, as_of_iso),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "history_id": row[0], "persona_summary": row[1], "style_summary": row[2],
        "boundary_summary": row[3], "valid_from": row[4], "valid_to": row[5],
    }
