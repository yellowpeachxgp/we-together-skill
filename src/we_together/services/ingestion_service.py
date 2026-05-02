import hashlib
import json
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.importers.text_chat_importer import import_text_chat
from we_together.importers.text_narration_importer import import_narration_text
from we_together.services.identity_link_service import upsert_identity_link
from we_together.services.ingestion_helpers import (
    persist_import_job,
    persist_patch_record,
    persist_raw_evidence,
    persist_snapshot_with_entities,
)
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import (
    build_patch,
    infer_narration_patches,
    infer_text_chat_patches,
)
from we_together.services.snapshot_service import build_snapshot, build_snapshot_entities


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


def ingest_narration(
    db_path: Path,
    text: str,
    source_name: str,
    scene_id: str | None = None,
) -> dict:
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
    snapshot_entity_rows = []

    conn = connect(db_path)
    persist_import_job(
        conn,
        import_job_id=import_job_id,
        source_type="narration",
        source_platform="manual",
        operator="system",
        status="completed",
        stats=import_result["stats"],
        now=now,
    )
    persist_raw_evidence(
        conn,
        evidence=evidence,
        import_job_id=import_job_id,
        content_hash=hashlib.sha256(text.encode()).hexdigest(),
        file_path=None,
        now=now,
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
            scene_id,
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
        conn.commit()
        conn.close()
        upsert_identity_link(
            db_path=db_path,
            person_id=person_id,
            platform="narration",
            external_id=name,
            display_name=name,
            confidence=0.7,
        )
        conn = connect(db_path)

    if len(person_ids) >= 2:
        relation_ids = []
        for core_type, label in relation_hints or [("unknown", "提及关系")]:
            relation_id = f"relation_{uuid.uuid5(uuid.NAMESPACE_URL, f'{core_type}:{person_ids[0]}:{person_ids[1]}').hex}"
            relation_ids.append(relation_id)
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
        conn.commit()
        conn.close()

        inferred_patches = infer_narration_patches(
            source_event_id=event_id,
            text=text,
            person_ids=person_ids,
            relation_ids=relation_ids,
        )
        for inferred_patch in inferred_patches:
            apply_patch_record(db_path=db_path, patch=inferred_patch)

        memory_patch = next(
            (patch_item for patch_item in inferred_patches if patch_item["operation"] == "create_memory"),
            None,
        )
        memory_id = memory_patch["payload_json"]["memory_id"] if memory_patch else None
        snapshot_entities = [("event", event_id)]
        if scene_id is not None:
            snapshot_entities.append(("scene", scene_id))
        snapshot_entities.extend(("person", person_id) for person_id in person_ids)
        snapshot_entities.extend(("relation", relation_id) for relation_id in relation_ids)
        if memory_id is not None:
            snapshot_entities.append(("memory", memory_id))
        snapshot_entity_rows = build_snapshot_entities(
            snapshot_id=snapshot_id,
            entities=snapshot_entities,
        )
        conn = connect(db_path)
        if memory_id is not None:
            for person_id in person_ids[:2]:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO memory_owners(memory_id, owner_type, owner_id, role_label)
                    VALUES(?, ?, ?, ?)
                    """,
                    (memory_id, "person", person_id, "shared"),
                )

    if conn is None:
        conn = connect(db_path)
    persist_patch_record(conn, patch=patch, now=now)
    persist_snapshot_with_entities(conn, snapshot=snapshot, entity_rows=snapshot_entity_rows)
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


def ingest_text_chat(db_path: Path, transcript: str, source_name: str) -> dict:
    now = datetime.now(UTC).isoformat()
    import_job_id = f"import_{uuid.uuid4().hex}"
    import_result = import_text_chat(transcript=transcript, source_name=source_name)
    evidence = import_result["raw_evidences"][0]
    evidence_id = evidence["evidence_id"]

    conn = connect(db_path)
    snapshot_entity_rows = []
    persist_import_job(
        conn,
        import_job_id=import_job_id,
        source_type="text_chat",
        source_platform="manual",
        operator="system",
        status="completed",
        stats=import_result["stats"],
        now=now,
    )
    persist_raw_evidence(
        conn,
        evidence=evidence,
        import_job_id=import_job_id,
        content_hash=hashlib.sha256(transcript.encode()).hexdigest(),
        file_path=None,
        now=now,
    )

    people = []
    person_ids_by_name = {}
    for identity in import_result["identity_candidates"]:
        name = identity["display_name"]
        person_id = f"person_{uuid.uuid5(uuid.NAMESPACE_URL, name).hex}"
        people.append(person_id)
        person_ids_by_name[name] = person_id
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
                json.dumps({"source": "text_chat"}, ensure_ascii=False),
                now,
                now,
            ),
        )
        conn.commit()
        conn.close()
        upsert_identity_link(
            db_path=db_path,
            person_id=person_id,
            platform="text_chat",
            external_id=name,
            display_name=name,
            confidence=0.8,
        )
        conn = connect(db_path)

    event_count = 0
    event_ids = []
    for event_candidate in import_result["event_candidates"]:
        event_id = f"evt_{uuid.uuid4().hex}"
        event_ids.append(event_id)
        patch = build_patch(
            source_event_id=event_id,
            target_type="event",
            target_id=event_id,
            operation="create_entity",
            payload={"evidence_id": evidence_id, "summary": event_candidate["summary"]},
            confidence=event_candidate["confidence"],
            reason="text chat import",
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
                "message_imported",
                "text_chat",
                None,
                None,
                event_candidate["time_hint"],
                event_candidate["summary"],
                "visible",
                event_candidate["confidence"],
                0,
                json.dumps([evidence_id], ensure_ascii=False),
                json.dumps({"actor_candidates": event_candidate["actor_candidates"]}, ensure_ascii=False),
                now,
            ),
        )
        for actor_name in event_candidate["actor_candidates"]:
            person_id = person_ids_by_name.get(actor_name)
            if not person_id:
                continue
            conn.execute(
                """
                INSERT OR IGNORE INTO event_participants(event_id, person_id, participant_role)
                VALUES(?, ?, ?)
                """,
                (event_id, person_id, "speaker"),
            )
        persist_patch_record(conn, patch=patch, now=now)
        event_count += 1

    snapshot_id = f"snap_{uuid.uuid4().hex}"

    if len(people) >= 2:
        relation_id = f"relation_{uuid.uuid5(uuid.NAMESPACE_URL, f'text_chat:{people[0]}:{people[1]}').hex}"
        person_names = [identity["display_name"] for identity in import_result["identity_candidates"][:2]]
        relation_summary = f"{person_names[0]} 与 {person_names[1]} 在文本聊天中存在直接互动"
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
                "interaction",
                "聊天关系",
                relation_summary,
                "bidirectional",
                0.3,
                0.3,
                "known",
                "active",
                None,
                None,
                0.5,
                json.dumps({"source": "text_chat"}, ensure_ascii=False),
                now,
                now,
            ),
        )
        for event_id in event_ids:
            conn.execute(
                """
                INSERT OR IGNORE INTO event_targets(event_id, target_type, target_id, impact_hint)
                VALUES(?, ?, ?, ?)
                """,
                (event_id, "relation", relation_id, "聊天关系"),
            )
        conn.commit()
        conn.close()

        inferred_patches = infer_text_chat_patches(
            source_event_id=event_id,
            transcript=transcript,
            person_ids=people,
            relation_id=relation_id,
        )
        for inferred_patch in inferred_patches:
            apply_patch_record(db_path=db_path, patch=inferred_patch)

        memory_patch = next(
            (patch_item for patch_item in inferred_patches if patch_item["operation"] == "create_memory"),
            None,
        )
        memory_id = memory_patch["payload_json"]["memory_id"] if memory_patch else None
        snapshot_entities = [("event", event_id) for event_id in event_ids]
        snapshot_entities.extend(("person", person_id) for person_id in people)
        snapshot_entities.append(("relation", relation_id))
        if memory_id:
            snapshot_entities.append(("memory", memory_id))
        snapshot_entity_rows = build_snapshot_entities(
            snapshot_id=snapshot_id,
            entities=snapshot_entities,
        )
        conn = connect(db_path)
        if memory_id:
            for person_id in people[:2]:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO memory_owners(memory_id, owner_type, owner_id, role_label)
                    VALUES(?, ?, ?, ?)
                    """,
                    (memory_id, "person", person_id, "shared"),
                )

    graph_hash = hashlib.sha256(f"{import_job_id}:{evidence_id}:{event_count}".encode()).hexdigest()
    snapshot = build_snapshot(
        snapshot_id=snapshot_id,
        based_on_snapshot_id=None,
        trigger_event_id=None,
        summary="after text chat import",
        graph_hash=graph_hash,
    )
    persist_snapshot_with_entities(conn, snapshot=snapshot, entity_rows=snapshot_entity_rows)
    conn.commit()
    conn.close()

    return {
        "import_job_id": import_job_id,
        "evidence_id": evidence_id,
        "event_count": event_count,
        "person_ids": people,
        "snapshot_id": snapshot_id,
    }
