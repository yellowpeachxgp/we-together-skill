"""Shared persistence helpers for ingestion services.

These functions extract the duplicated INSERT SQL found across
ingestion_service.py and email_ingestion_service.py.
"""

import json
import sqlite3


def persist_import_job(
    conn: sqlite3.Connection,
    *,
    import_job_id: str,
    source_type: str,
    source_platform: str,
    operator: str,
    status: str,
    stats: dict,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO import_jobs(
            import_job_id, source_type, source_platform, operator, status,
            stats_json, error_log, started_at, finished_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            import_job_id,
            source_type,
            source_platform,
            operator,
            status,
            json.dumps(stats, ensure_ascii=False),
            None,
            now,
            now,
        ),
    )


def persist_raw_evidence(
    conn: sqlite3.Connection,
    *,
    evidence: dict,
    import_job_id: str,
    content_hash: str,
    file_path: str | None,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO raw_evidences(
            evidence_id, import_job_id, source_type, source_platform, source_locator,
            content_type, normalized_text, timestamp, file_path, content_hash,
            metadata_json, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            evidence["evidence_id"],
            import_job_id,
            evidence["source_type"],
            evidence["source_platform"],
            evidence["source_locator"],
            evidence["content_type"],
            evidence["normalized_text"],
            now,
            file_path,
            content_hash,
            json.dumps({}, ensure_ascii=False),
            now,
        ),
    )


def persist_patch_record(
    conn: sqlite3.Connection,
    *,
    patch: dict,
    now: str,
) -> None:
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


def persist_snapshot_with_entities(
    conn: sqlite3.Connection,
    *,
    snapshot: dict,
    entity_rows: list[dict],
) -> None:
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
    for row in entity_rows:
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
