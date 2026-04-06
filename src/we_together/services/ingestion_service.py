from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import uuid

from we_together.db.connection import connect
from we_together.importers.text_narration_importer import import_narration_text
from we_together.services.patch_service import build_patch
from we_together.services.snapshot_service import build_snapshot


def _extract_people(text: str) -> list[str]:
    pattern = r"(小[\u4e00-\u9fff])和(小[\u4e00-\u9fff])"
    match = re.search(pattern, text)
    if match:
        return [match.group(1), match.group(2)]
    fallback_patterns = [
        r"([\u4e00-\u9fff]{2,3})和([\u4e00-\u9fff]{2,3})是",
        r"([\u4e00-\u9fff]{2,3})和([\u4e00-\u9fff]{2,3})以前",
    ]
    for pattern in fallback_patterns:
        match = re.search(pattern, text)
        if match:
            return [match.group(1), match.group(2)]
    return []


def _extract_relation_hints(text: str) -> list[tuple[str, str]]:
    hints = []
    if "同事" in text:
        hints.append(("work", "同事"))
    if "朋友" in text:
        hints.append(("friendship", "朋友"))
    return hints


def ingest_narration(db_path: Path, text: str, source_name: str) -> dict:
    now = datetime.now(UTC).isoformat()
    import_job_id = f"import_{uuid.uuid4().hex}"
    import_result = import_narration_text(text=text, source_name=source_name)
    evidence = import_result["raw_evidences"][0]
    evidence_id = evidence["evidence_id"]
    event_id = f"evt_{uuid.uuid4().hex}"
    people = _extract_people(text)
    relation_hints = _extract_relation_hints(text)
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
    person_ids = []
    for name in people:
        person_id = f"person_{uuid.uuid5(uuid.NAMESPACE_URL, name).hex}"
        person_ids.append(person_id)
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
                name,
                "active",
                None,
                None,
                None,
                None,
                None,
                None,
                0.6,
                json.dumps({"source": "narration"}, ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO event_participants(event_id, person_id, participant_role)
            VALUES(?, ?, ?)
            """,
            (event_id, person_id, "mentioned"),
        )

    if len(person_ids) >= 2:
        for core_type, label in relation_hints or [("unknown", "提及关系")]:
            relation_id = f"relation_{uuid.uuid5(uuid.NAMESPACE_URL, f'{core_type}:{person_ids[0]}:{person_ids[1]}').hex}"
            conn.execute(
                """
                INSERT OR IGNORE INTO relations(
                    relation_id, core_type, custom_label, summary, directionality,
                    strength, stability, visibility, status, time_start, time_end,
                    confidence, metadata_json, created_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    relation_id,
                    core_type,
                    label,
                    text,
                    "bidirectional",
                    0.5,
                    0.5,
                    "known",
                    "active",
                    None,
                    None,
                    0.7,
                    json.dumps({"source_event_id": event_id}, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            for person_id in person_ids[:2]:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO event_targets(event_id, target_type, target_id, impact_hint)
                    VALUES(?, ?, ?, ?)
                    """,
                    (event_id, "relation", relation_id, label),
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
        "person_ids": person_ids,
    }
