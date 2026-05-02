"""冷记忆归档：把长期未激活的 memory 从 memories 移入 cold_memories。

规则：
  - updated_at 早于 window_days 前
  - status != 'active' 或 relevance_score < 阈值 均可归档
  - 默认只归档 'inactive' 或 'archived' 状态，避免误杀

API：
  - archive_cold_memories(db_path, window_days=180, relevance_threshold=0.15) -> dict
  - restore_cold_memory(db_path, memory_id) -> bool

retrieval 默认不加载 cold_memories；include_cold=True 时附带 cold 列表。
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from we_together.db.connection import connect


def _now() -> str:
    return datetime.now(UTC).isoformat()


def archive_cold_memories(
    db_path: Path,
    *,
    window_days: int = 180,
    relevance_threshold: float = 0.15,
    limit: int = 500,
) -> dict:
    cutoff = (datetime.now(UTC) - timedelta(days=window_days)).isoformat()
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT memory_id, memory_type, summary, emotional_tone, relevance_score,
               confidence, is_shared, metadata_json, created_at, updated_at, status
        FROM memories
        WHERE (status IN ('inactive', 'archived')
               OR (relevance_score IS NOT NULL AND relevance_score < ?))
          AND (updated_at IS NULL OR updated_at < ?)
        ORDER BY updated_at ASC
        LIMIT ?
        """,
        (relevance_threshold, cutoff, limit),
    ).fetchall()

    archived: list[str] = []
    now = _now()
    for r in rows:
        reason = (
            "low_relevance" if (r["relevance_score"] or 1.0) < relevance_threshold
            else f"status_{r['status']}"
        )
        conn.execute(
            """INSERT OR REPLACE INTO cold_memories(
                memory_id, memory_type, summary, emotional_tone, relevance_score,
                confidence, is_shared, metadata_json, original_created_at,
                original_updated_at, archived_at, archive_reason
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (r["memory_id"], r["memory_type"], r["summary"], r["emotional_tone"],
             r["relevance_score"], r["confidence"], r["is_shared"], r["metadata_json"],
             r["created_at"], r["updated_at"], now, reason),
        )
        owner_rows = conn.execute(
            "SELECT owner_type, owner_id, role_label FROM memory_owners WHERE memory_id = ?",
            (r["memory_id"],),
        ).fetchall()
        for o in owner_rows:
            conn.execute(
                "INSERT OR REPLACE INTO cold_memory_owners(memory_id, owner_type, owner_id, role_label) "
                "VALUES(?, ?, ?, ?)",
                (r["memory_id"], o["owner_type"], o["owner_id"], o["role_label"]),
            )
        conn.execute("DELETE FROM memory_owners WHERE memory_id = ?", (r["memory_id"],))
        conn.execute("DELETE FROM memories WHERE memory_id = ?", (r["memory_id"],))
        archived.append(r["memory_id"])

    conn.commit()
    conn.close()
    return {
        "archived_count": len(archived),
        "archived_ids": archived,
        "window_days": window_days,
    }


def restore_cold_memory(db_path: Path, memory_id: str) -> bool:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM cold_memories WHERE memory_id = ?", (memory_id,),
    ).fetchone()
    if row is None:
        conn.close()
        return False
    now = _now()
    conn.execute(
        """INSERT OR REPLACE INTO memories(
            memory_id, memory_type, summary, emotional_tone, relevance_score,
            confidence, is_shared, status, metadata_json, created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?, 'active', ?, ?, ?)""",
        (row["memory_id"], row["memory_type"], row["summary"], row["emotional_tone"],
         row["relevance_score"], row["confidence"], row["is_shared"],
         row["metadata_json"], row["original_created_at"] or now, now),
    )
    owner_rows = conn.execute(
        "SELECT owner_type, owner_id, role_label FROM cold_memory_owners WHERE memory_id = ?",
        (memory_id,),
    ).fetchall()
    for o in owner_rows:
        conn.execute(
            "INSERT OR REPLACE INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, ?, ?, ?)",
            (memory_id, o["owner_type"], o["owner_id"], o["role_label"]),
        )
    conn.execute("DELETE FROM cold_memories WHERE memory_id = ?", (memory_id,))
    conn.execute("DELETE FROM cold_memory_owners WHERE memory_id = ?", (memory_id,))
    conn.commit()
    conn.close()
    return True


def list_cold_memories(db_path: Path, *, limit: int = 100) -> list[dict]:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT memory_id, memory_type, summary, archived_at, archive_reason, metadata_json "
        "FROM cold_memories ORDER BY archived_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "memory_id": r["memory_id"],
            "memory_type": r["memory_type"],
            "summary": r["summary"],
            "archived_at": r["archived_at"],
            "archive_reason": r["archive_reason"],
            "metadata": json.loads(r["metadata_json"] or "{}"),
        }
        for r in rows
    ]
