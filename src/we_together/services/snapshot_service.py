import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect


def build_snapshot(
    snapshot_id: str,
    based_on_snapshot_id: str | None,
    trigger_event_id: str | None,
    summary: str,
    graph_hash: str,
) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "based_on_snapshot_id": based_on_snapshot_id,
        "trigger_event_id": trigger_event_id,
        "summary": summary,
        "graph_hash": graph_hash,
        "created_at": datetime.now(UTC).isoformat(),
    }


def build_snapshot_entities(
    snapshot_id: str,
    entities: list[tuple[str, str]],
) -> list[dict]:
    rows = []
    seen = set()
    for entity_type, entity_id in entities:
        key = (entity_type, entity_id)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "snapshot_id": snapshot_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "entity_hash": hashlib.sha256(f"{entity_type}:{entity_id}".encode()).hexdigest(),
            }
        )
    return rows


def list_snapshots(db_path: Path, limit: int = 50) -> list[dict]:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT snapshot_id, based_on_snapshot_id, trigger_event_id,
               summary, graph_hash, created_at
        FROM snapshots
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "snapshot_id": row["snapshot_id"],
            "based_on_snapshot_id": row["based_on_snapshot_id"],
            "trigger_event_id": row["trigger_event_id"],
            "summary": row["summary"],
            "graph_hash": row["graph_hash"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def rollback_to_snapshot(db_path: Path, snapshot_id: str) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row

    snap_row = conn.execute(
        "SELECT created_at FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if snap_row is None:
        conn.close()
        raise ValueError(f"Snapshot not found: {snapshot_id}")

    snapshot_time = snap_row["created_at"]

    # 标记 snapshot 之后的 patches 为 rolled_back
    rolled_patches = conn.execute(
        "UPDATE patches SET status = 'rolled_back' WHERE applied_at > ? AND status = 'applied'",
        (snapshot_time,),
    ).rowcount

    # 删除 snapshot 之后写入的 states
    conn.execute("DELETE FROM states WHERE updated_at > ?", (snapshot_time,))

    # 删除后续 snapshots
    conn.execute("DELETE FROM snapshots WHERE created_at > ?", (snapshot_time,))

    # 清除 retrieval cache
    conn.execute("DELETE FROM retrieval_cache")

    conn.commit()
    conn.close()
    return {
        "rolled_back_to": snapshot_id,
        "rolled_back_patch_count": rolled_patches,
    }


def replay_patches_after_snapshot(db_path: Path, snapshot_id: str) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row

    snap_row = conn.execute(
        "SELECT created_at FROM snapshots WHERE snapshot_id = ?",
        (snapshot_id,),
    ).fetchone()
    if snap_row is None:
        conn.close()
        raise ValueError(f"Snapshot not found: {snapshot_id}")

    # 查询 rolled_back 的 patches（按 created_at 排序）
    rolled_patches = conn.execute(
        """
        SELECT patch_id, source_event_id, target_type, target_id,
               operation, payload_json, confidence, reason, created_at
        FROM patches
        WHERE status = 'rolled_back'
        AND created_at > ?
        ORDER BY created_at ASC
        """,
        (snap_row["created_at"],),
    ).fetchall()
    conn.close()

    # 逐个重新 apply
    from we_together.services.patch_applier import apply_patch_record

    replayed = 0
    for row in rolled_patches:
        patch = {
            "patch_id": row["patch_id"],
            "source_event_id": row["source_event_id"],
            "target_type": row["target_type"],
            "target_id": row["target_id"],
            "operation": row["operation"],
            "payload_json": json.loads(row["payload_json"]),
            "confidence": row["confidence"],
            "reason": row["reason"],
            "status": "pending",
            "created_at": row["created_at"],
            "applied_at": None,
        }
        # 将 patch 状态重置为 pending 以便重新应用
        reset_conn = connect(db_path)
        reset_conn.execute(
            "UPDATE patches SET status = 'pending', applied_at = NULL WHERE patch_id = ?",
            (row["patch_id"],),
        )
        reset_conn.commit()
        reset_conn.close()

        apply_patch_record(db_path=db_path, patch=patch)
        replayed += 1

    return {"replayed_count": replayed}
