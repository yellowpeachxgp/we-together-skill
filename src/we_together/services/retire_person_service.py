"""SM-4 Retire person service：人物退场生命周期。

动作（按顺序）：
  1. 该 person 的 active memories 走 memory_archive_service 归档
  2. 该 person 的 active relations.strength *= 0.3（fade）
  3. scene_participants 中此 person 标 activation_state='latent'
  4. persons.status = 'retired'
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect


def retire_person(
    db_path: Path, person_id: str, *, reason: str = "retired",
) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT person_id, primary_name, status FROM persons WHERE person_id = ?",
        (person_id,),
    ).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"person not found: {person_id}")
    if row["status"] == "retired":
        conn.close()
        return {"already_retired": True, "person_id": person_id}

    now = datetime.now(UTC).isoformat()

    # 1. memories → 标 inactive（由后续 archive_cold_memories 批量迁移）
    mem_rows = conn.execute(
        "SELECT memory_id FROM memory_owners WHERE owner_id = ? AND owner_type = 'person'",
        (person_id,),
    ).fetchall()
    mem_ids = [m[0] for m in mem_rows]
    for mid in mem_ids:
        conn.execute(
            "UPDATE memories SET status = 'inactive', updated_at = ? WHERE memory_id = ?",
            (now, mid),
        )

    # 2. relations strength 衰减（通过 event_targets→relation 反查）
    rel_rows = conn.execute(
        """SELECT DISTINCT r.relation_id, r.strength FROM relations r
           JOIN event_targets et ON et.target_type='relation' AND et.target_id=r.relation_id
           JOIN event_participants ep ON ep.event_id = et.event_id
           WHERE ep.person_id = ? AND r.status = 'active'""",
        (person_id,),
    ).fetchall()
    for r in rel_rows:
        new_strength = (r["strength"] or 0.5) * 0.3
        conn.execute(
            "UPDATE relations SET strength = ?, updated_at = ? WHERE relation_id = ?",
            (new_strength, now, r["relation_id"]),
        )

    # 3. scene_participants → latent
    conn.execute(
        "UPDATE scene_participants SET activation_state = 'latent' WHERE person_id = ?",
        (person_id,),
    )

    # 4. person → retired
    conn.execute(
        "UPDATE persons SET status = 'retired', updated_at = ? WHERE person_id = ?",
        (now, person_id),
    )

    conn.commit()
    conn.close()
    return {
        "person_id": person_id,
        "primary_name": row["primary_name"],
        "memories_deactivated": len(mem_ids),
        "relations_faded": len(rel_rows),
        "reason": reason,
    }
