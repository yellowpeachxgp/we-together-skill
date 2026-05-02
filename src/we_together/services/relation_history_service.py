"""Relation history：按时间 bucket 聚合 relation.strength 变化（基于 patches.applied_at）。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.db.connection import connect


def get_relation_strength_series(
    db_path: Path, relation_id: str, *, bucket: str = "week",
) -> list[dict]:
    """bucket ∈ {'day','week','month'}：按 bucket 取每段的最后一个值。"""
    assert bucket in ("day", "week", "month")
    fmt = {"day": "%Y-%m-%d", "week": "%Y-%W", "month": "%Y-%m"}[bucket]
    conn = connect(db_path)
    rows = conn.execute(
        f"""
        SELECT strftime('{fmt}', p.applied_at) AS bucket,
               json_extract(p.payload_json, '$.strength') AS strength,
               p.applied_at
        FROM patches p
        WHERE p.target_type = 'relation'
          AND p.target_id = ?
          AND p.status = 'applied'
          AND json_extract(p.payload_json, '$.strength') IS NOT NULL
        ORDER BY p.applied_at ASC
        """,
        (relation_id,),
    ).fetchall()
    conn.close()

    by_bucket: dict[str, tuple[float, str]] = {}
    for b, s, at in rows:
        if s is None:
            continue
        by_bucket[b] = (float(s), at)
    return [
        {"bucket": b, "strength": v[0], "applied_at": v[1]}
        for b, v in sorted(by_bucket.items())
    ]


def list_relations_with_changes(
    db_path: Path, *, limit: int = 20,
) -> list[dict]:
    conn = connect(db_path)
    rows = conn.execute(
        """SELECT target_id, COUNT(*) AS change_count
           FROM patches
           WHERE target_type = 'relation' AND status = 'applied'
             AND json_extract(payload_json, '$.strength') IS NOT NULL
           GROUP BY target_id
           ORDER BY change_count DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [{"relation_id": r[0], "change_count": r[1]} for r in rows]
