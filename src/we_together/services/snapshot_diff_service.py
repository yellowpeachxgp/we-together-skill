"""Snapshot diff 服务：比较两个 snapshot 之间发生了什么变化。

输出：
  - patches：两个 snapshot 之间应用的 patch 列表（from.created_at < applied_at <= to.created_at）
  - entity_delta: snapshot_entities 的新增/删除对比
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.db.connection import connect


def diff_snapshots(db_path: Path, from_snapshot_id: str, to_snapshot_id: str) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row

    from_row = conn.execute(
        "SELECT created_at FROM snapshots WHERE snapshot_id = ?", (from_snapshot_id,)
    ).fetchone()
    to_row = conn.execute(
        "SELECT created_at FROM snapshots WHERE snapshot_id = ?", (to_snapshot_id,)
    ).fetchone()
    if not from_row or not to_row:
        conn.close()
        raise ValueError("one or both snapshots not found")

    from_ts = from_row["created_at"]
    to_ts = to_row["created_at"]
    if from_ts > to_ts:
        from_ts, to_ts = to_ts, from_ts
        from_snapshot_id, to_snapshot_id = to_snapshot_id, from_snapshot_id

    patches = conn.execute(
        """
        SELECT patch_id, operation, target_type, target_id, reason,
               applied_at, status
        FROM patches
        WHERE applied_at IS NOT NULL AND applied_at > ? AND applied_at <= ?
        ORDER BY applied_at ASC
        """,
        (from_ts, to_ts),
    ).fetchall()

    from_entities = {
        (r["entity_type"], r["entity_id"])
        for r in conn.execute(
            "SELECT entity_type, entity_id FROM snapshot_entities WHERE snapshot_id = ?",
            (from_snapshot_id,),
        ).fetchall()
    }
    to_entities = {
        (r["entity_type"], r["entity_id"])
        for r in conn.execute(
            "SELECT entity_type, entity_id FROM snapshot_entities WHERE snapshot_id = ?",
            (to_snapshot_id,),
        ).fetchall()
    }
    conn.close()

    added = [
        {"entity_type": t, "entity_id": i} for (t, i) in sorted(to_entities - from_entities)
    ]
    removed = [
        {"entity_type": t, "entity_id": i} for (t, i) in sorted(from_entities - to_entities)
    ]

    return {
        "from_snapshot_id": from_snapshot_id,
        "to_snapshot_id": to_snapshot_id,
        "patch_count": len(patches),
        "patches": [
            {
                "patch_id": row["patch_id"],
                "operation": row["operation"],
                "target_type": row["target_type"],
                "target_id": row["target_id"],
                "reason": row["reason"],
                "applied_at": row["applied_at"],
                "status": row["status"],
            }
            for row in patches
        ],
        "entity_delta": {
            "added": added,
            "removed": removed,
        },
    }
