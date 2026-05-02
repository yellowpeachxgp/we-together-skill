"""Perceived memory：同一 event 不同 person 视角的记忆。

通过 memories.perspective_person_id 列区分。原有 perspective_person_id=NULL 的
memory 仍视为"集体视角"，向后兼容。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect


def _now() -> str:
    return datetime.now(UTC).isoformat()


def write_perceived_memory(
    db_path: Path,
    *,
    perspective_person_id: str,
    summary: str,
    memory_type: str = "perceived_memory",
    relevance_score: float = 0.6,
    confidence: float = 0.6,
    owners: list[str] | None = None,
    metadata: dict | None = None,
) -> str:
    mid = f"mem_pc_{uuid.uuid4().hex[:12]}"
    conn = connect(db_path)
    now = _now()
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, perspective_person_id,
           created_at, updated_at)
           VALUES(?, ?, ?, ?, ?, 0, 'active', ?, ?, ?, ?)""",
        (mid, memory_type, summary, relevance_score, confidence,
         str(metadata or {}), perspective_person_id, now, now),
    )
    for pid in owners or [perspective_person_id]:
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, 'perceiver')",
            (mid, pid),
        )
    conn.commit()
    conn.close()
    return mid


def query_memories_by_perspective(
    db_path: Path, *, person_id: str, include_collective: bool = True, limit: int = 50,
) -> list[dict]:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    if include_collective:
        rows = conn.execute(
            """SELECT memory_id, memory_type, summary, relevance_score, confidence,
               perspective_person_id
               FROM memories
               WHERE status = 'active'
                 AND (perspective_person_id = ? OR perspective_person_id IS NULL)
               ORDER BY created_at DESC LIMIT ?""",
            (person_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT memory_id, memory_type, summary, relevance_score, confidence,
               perspective_person_id
               FROM memories
               WHERE status = 'active' AND perspective_person_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (person_id, limit),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
