from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import uuid

from we_together.db.connection import connect
from we_together.importers.text_narration_importer import import_narration_text
from we_together.services.patch_service import build_patch
from we_together.services.snapshot_service import build_snapshot


def ingest_narration(db_path: Path, text: str, source_name: str) -> dict:
    now = datetime.now(UTC).isoformat()
    import_job_id = f"import_{uuid.uuid4().hex}"
    import_result = import_narration_text(text=text, source_name=source_name)
    evidence = import_result["raw_evidences"][0]
    evidence_id = evidence["evidence_id"]
    event_id = f"evt_{uuid.uuid4().hex}"
    patch = build_patch(
        source_event_id=event_id,
        target_type="event",
        target_id=event_id,
        operation="create_entity",
        payload={"evidence_id": evidence_id, "summary": text},
        confidence=1.0,
        reason="narration import",
    )
    snapshot_id = f"snap_{uuid.uuid4().hex}"
    graph_hash = hashlib.sha256(f"{import_job_id}:{evidence_id}:{event_id}".encode()).hexdigest()
    snapshot = build_snapshot(
        snapshot_id=snapshot_id,
        based_on_snapshot_id=None,
        trigger_event_id=event_id,
        summary="after narration import",
        graph_hash=graph_hash,
    )

    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO import_jobs(
            import_job_id, source_type, source_platform, operator, status,
            stats_json, error_log, started_at, finished_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            import_job_id,
            "narration",
            "manual",
            "system",
            "completed",
            json.dumps(import_result["stats"], ensure_ascii=False),
            None,
            now,
            now,
        ),
    )
    conn.execute(
        """
        INSERT INTO raw_evidences(
            evidence_id, import_job_id, source_type, source_platform, source_locator,
            content_type, normalized_text, timestamp, file_path, content_hash,
            metadata_json, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidence_id,
            import_job_id,
            evidence["source_type"],
            evidence["source_platform"],
            evidence["source_locator"],
            evidence["content_type"],
            evidence["normalized_text"],
            now,
            None,
            hashlib.sha256(text.encode()).hexdigest(),
            json.dumps({}, ensure_ascii=False),
            now,
        ),
    )
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
            "narration_imported",
            "narration",
            None,
            None,
            now,
            text,
            "visible",
            1.0,
            0,
            json.dumps([evidence_id], ensure_ascii=False),
            json.dumps({"source_name": source_name}, ensure_ascii=False),
            now,
        ),
    )
    conn.execute(
        """
        INSERT INTO patches(
            patch_id, source_event_id, target_type, target_id,
            operation, payload_json, confidence, reason, status,
            created_at, applied_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patch["patch_id"],
            patch["source_event_id"],
            patch["target_type"],
            patch["target_id"],
            patch["operation"],
            json.dumps(patch["payload_json"], ensure_ascii=False),
            patch["confidence"],
            patch["reason"],
            "applied",
            patch["created_at"],
            now,
        ),
    )
    conn.execute(
        """
        INSERT INTO snapshots(
            snapshot_id, based_on_snapshot_id, trigger_event_id,
            summary, graph_hash, created_at
        ) VALUES(?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot["snapshot_id"],
            snapshot["based_on_snapshot_id"],
            snapshot["trigger_event_id"],
            snapshot["summary"],
            snapshot["graph_hash"],
            snapshot["created_at"],
        ),
    )
    conn.commit()
    conn.close()

    return {
        "import_job_id": import_job_id,
        "evidence_id": evidence_id,
        "event_id": event_id,
        "patch_id": patch["patch_id"],
        "snapshot_id": snapshot_id,
    }
