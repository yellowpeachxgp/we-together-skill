"""federation_write_service（Phase 67 FW）：联邦写路径最小闭环。

原则：
- 先写 event
- 再 build/apply patch(create_memory)
- 再补 memory_owners + snapshot
- 默认由 HTTP 层显式开启，不在 server 中默认暴露
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.runtime.sqlite_retrieval import invalidate_runtime_retrieval_cache
from we_together.services.ingestion_helpers import persist_snapshot_with_entities
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.snapshot_service import build_snapshot, build_snapshot_entities


def create_shared_memory_from_federation(
    db_path: Path,
    *,
    summary: str,
    owner_person_ids: list[str],
    source_skill_name: str | None = None,
    source_locator: str | None = None,
    scene_id: str | None = None,
    memory_type: str = "shared_memory",
    relevance_score: float = 0.8,
    confidence: float = 0.8,
    metadata: dict | None = None,
) -> dict:
    summary = summary.strip()
    if not summary:
        raise ValueError("summary required")

    owner_ids = list(dict.fromkeys(owner_person_ids))
    if not owner_ids:
        raise ValueError("owner_person_ids required")

    conn = connect(db_path)
    conn.row_factory = None
    try:
        missing = [
            owner_id
            for owner_id in owner_ids
            if conn.execute(
                "SELECT 1 FROM persons WHERE person_id = ? LIMIT 1",
                (owner_id,),
            ).fetchone()
            is None
        ]
        if missing:
            raise ValueError(f"unknown owner_person_ids: {missing}")
    finally:
        conn.close()

    now = datetime.now(UTC).isoformat()
    event_id = f"evt_fed_{uuid.uuid4().hex}"
    memory_id = f"memory_{uuid.uuid4().hex}"
    snapshot_id = f"snap_fed_{uuid.uuid4().hex}"

    event_metadata = {
        "source": "federation_write",
        "source_skill_name": source_skill_name,
        "source_locator": source_locator,
        "metadata": metadata or {},
    }

    conn = connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO events(
                event_id, event_type, source_type, scene_id, group_id,
                timestamp, summary, visibility_level, confidence, is_structured,
                raw_evidence_refs_json, metadata_json, created_at
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                "federation_memory_ingested",
                "federation",
                scene_id,
                None,
                now,
                summary,
                "visible",
                confidence,
                1,
                json.dumps([], ensure_ascii=False),
                json.dumps(event_metadata, ensure_ascii=False),
                now,
            ),
        )
        for owner_id in owner_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO event_participants(event_id, person_id, participant_role)
                VALUES(?, ?, ?)
                """,
                (event_id, owner_id, "owner"),
            )
        if scene_id:
            conn.execute(
                """
                INSERT OR IGNORE INTO event_targets(event_id, target_type, target_id, impact_hint)
                VALUES(?, ?, ?, ?)
                """,
                (event_id, "scene", scene_id, "federation memory write"),
            )
        conn.commit()
    finally:
        conn.close()

    patch = build_patch(
        source_event_id=event_id,
        target_type="memory",
        target_id=memory_id,
        operation="create_memory",
        payload={
            "memory_id": memory_id,
            "memory_type": memory_type,
            "summary": summary,
            "relevance_score": relevance_score,
            "confidence": confidence,
            "is_shared": 1,
            "status": "active",
            "metadata_json": {
                "source_event_id": event_id,
                "source": "federation_write",
                "source_skill_name": source_skill_name,
                "source_locator": source_locator,
                "metadata": metadata or {},
            },
        },
        confidence=confidence,
        reason="federation write create_memory",
    )
    apply_patch_record(db_path=db_path, patch=patch)

    graph_hash = hashlib.sha256(
        f"{event_id}:{memory_id}:{','.join(owner_ids)}".encode()
    ).hexdigest()
    snapshot = build_snapshot(
        snapshot_id=snapshot_id,
        based_on_snapshot_id=None,
        trigger_event_id=event_id,
        summary="after federation memory write",
        graph_hash=graph_hash,
    )
    entities = [("event", event_id), ("memory", memory_id)]
    entities.extend(("person", owner_id) for owner_id in owner_ids)
    if scene_id:
        entities.append(("scene", scene_id))
    entity_rows = build_snapshot_entities(snapshot_id=snapshot_id, entities=entities)

    conn = connect(db_path)
    try:
        for owner_id in owner_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO memory_owners(memory_id, owner_type, owner_id, role_label)
                VALUES(?, ?, ?, ?)
                """,
                (memory_id, "person", owner_id, "shared"),
            )
        persist_snapshot_with_entities(conn, snapshot=snapshot, entity_rows=entity_rows)
        conn.commit()
    finally:
        conn.close()

    invalidate_runtime_retrieval_cache(db_path=db_path)
    return {
        "event_id": event_id,
        "patch_id": patch["patch_id"],
        "memory_id": memory_id,
        "snapshot_id": snapshot_id,
        "owner_count": len(owner_ids),
    }
