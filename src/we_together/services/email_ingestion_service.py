import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.importers.email_importer import import_email_file
from we_together.services.identity_link_service import upsert_identity_link
from we_together.services.ingestion_helpers import (
    persist_import_job,
    persist_patch_record,
    persist_raw_evidence,
    persist_snapshot_with_entities,
)
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch, infer_email_patches
from we_together.services.snapshot_service import build_snapshot, build_snapshot_entities


def ingest_email_file(db_path: Path, email_path: Path) -> dict:
    now = datetime.now(UTC).isoformat()
    import_job_id = f"import_{uuid.uuid4().hex}"
    import_result = import_email_file(email_path)
    evidence = import_result["raw_evidences"][0]
    identity = import_result["identity_candidates"][0]
    event = import_result["event_candidates"][0]
    evidence_id = evidence["evidence_id"]
    person_id = f"person_{uuid.uuid5(uuid.NAMESPACE_URL, identity['display_name']).hex}"
    event_id = f"evt_{uuid.uuid4().hex}"
    patch = build_patch(
        source_event_id=event_id,
        target_type="event",
        target_id=event_id,
        operation="create_entity",
        payload={"evidence_id": evidence_id, "summary": event["summary"]},
        confidence=event["confidence"],
        reason="email import",
    )
    snapshot_id = f"snap_{uuid.uuid4().hex}"
    graph_hash = hashlib.sha256(f"{import_job_id}:{evidence_id}:{event_id}".encode()).hexdigest()
    snapshot = build_snapshot(
        snapshot_id=snapshot_id,
        based_on_snapshot_id=None,
        trigger_event_id=event_id,
        summary="after email import",
        graph_hash=graph_hash,
    )
    snapshot_entity_rows = []

    conn = connect(db_path)
    persist_import_job(
        conn,
        import_job_id=import_job_id,
        source_type="email",
        source_platform="file",
        operator="system",
        status="completed",
        stats=import_result["stats"],
        now=now,
    )
    persist_raw_evidence(
        conn,
        evidence=evidence,
        import_job_id=import_job_id,
        content_hash=hashlib.sha256(evidence["normalized_text"].encode()).hexdigest(),
        file_path=str(email_path),
        now=now,
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            person_id,
            identity["display_name"],
            "active",
            None,
            None,
            None,
            None,
            None,
            None,
            0.7,
            json.dumps({"source": "email"}, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    upsert_identity_link(
        db_path=db_path,
        person_id=person_id,
        platform="email",
        external_id=identity["external_id"],
        display_name=identity["display_name"],
        confidence=identity["confidence"],
    )
    conn = connect(db_path)
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
            "email_imported",
            "email",
            None,
            None,
            now,
            event["summary"],
            "visible",
            event["confidence"],
            0,
            json.dumps([evidence_id], ensure_ascii=False),
            json.dumps({"actor_candidates": event["actor_candidates"]}, ensure_ascii=False),
            now,
        ),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO event_participants(event_id, person_id, participant_role)
        VALUES(?, ?, ?)
        """,
        (event_id, person_id, "sender"),
    )
    persist_patch_record(conn, patch=patch, now=now)
    persist_snapshot_with_entities(conn, snapshot=snapshot, entity_rows=snapshot_entity_rows)
    conn.commit()
    conn.close()

    inferred_patches = infer_email_patches(
        source_event_id=event_id,
        person_id=person_id,
        summary=event["summary"],
    )
    for inferred_patch in inferred_patches:
        apply_patch_record(db_path=db_path, patch=inferred_patch)

    memory_patch = next(
        (patch_item for patch_item in inferred_patches if patch_item["operation"] == "create_memory"),
        None,
    )
    memory_id = memory_patch["payload_json"]["memory_id"] if memory_patch else None
    if memory_id:
        snapshot_entity_rows = build_snapshot_entities(
            snapshot_id=snapshot_id,
            entities=[
                ("event", event_id),
                ("person", person_id),
                ("memory", memory_id),
            ],
        )
        conn = connect(db_path)
        conn.execute(
            """
            INSERT OR IGNORE INTO memory_owners(memory_id, owner_type, owner_id, role_label)
            VALUES(?, ?, ?, ?)
            """,
            (memory_id, "person", person_id, "shared"),
        )
        for row in snapshot_entity_rows:
            conn.execute(
                """
                INSERT INTO snapshot_entities(snapshot_id, entity_type, entity_id, entity_hash)
                VALUES(?, ?, ?, ?)
                """,
                (
                    row["snapshot_id"],
                    row["entity_type"],
                    row["entity_id"],
                    row["entity_hash"],
                ),
            )
        conn.commit()
        conn.close()

    return {
        "import_job_id": import_job_id,
        "evidence_id": evidence_id,
        "event_id": event_id,
        "person_id": person_id,
        "snapshot_id": snapshot_id,
    }
