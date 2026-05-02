import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.runtime.sqlite_retrieval import (
    build_runtime_retrieval_package_from_db,
    invalidate_runtime_retrieval_cache,
)
from we_together.services.ingestion_helpers import persist_snapshot_with_entities
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import infer_dialogue_patches
from we_together.services.snapshot_service import build_snapshot, build_snapshot_entities


def record_dialogue_event(
    db_path: Path,
    scene_id: str,
    user_input: str,
    response_text: str,
    speaking_person_ids: list[str] | None = None,
) -> dict:
    now = datetime.now(UTC).isoformat()
    event_id = f"evt_{uuid.uuid4().hex}"
    summary = f"用户: {user_input[:100]} | 回复: {response_text[:100]}"

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
            "dialogue_event",
            "dialogue",
            scene_id,
            None,
            now,
            summary,
            "visible",
            1.0,
            0,
            json.dumps([], ensure_ascii=False),
            json.dumps({
                "user_input": user_input,
                "response_text": response_text,
            }, ensure_ascii=False),
            now,
        ),
    )

    for person_id in (speaking_person_ids or []):
        conn.execute(
            """
            INSERT OR IGNORE INTO event_participants(event_id, person_id, participant_role)
            VALUES(?, ?, ?)
            """,
            (event_id, person_id, "speaker"),
        )

    conn.execute(
        """
        INSERT OR IGNORE INTO event_targets(event_id, target_type, target_id, impact_hint)
        VALUES(?, ?, ?, ?)
        """,
        (event_id, "scene", scene_id, "dialogue in scene"),
    )

    snapshot_id = f"snap_{uuid.uuid4().hex}"
    graph_hash = hashlib.sha256(f"dialogue:{event_id}:{scene_id}".encode()).hexdigest()
    snapshot = build_snapshot(
        snapshot_id=snapshot_id,
        based_on_snapshot_id=None,
        trigger_event_id=event_id,
        summary="after dialogue event",
        graph_hash=graph_hash,
    )
    snapshot_entities = [("event", event_id), ("scene", scene_id)]
    snapshot_entities.extend(("person", pid) for pid in (speaking_person_ids or []))
    entity_rows = build_snapshot_entities(
        snapshot_id=snapshot_id,
        entities=snapshot_entities,
    )
    persist_snapshot_with_entities(conn, snapshot=snapshot, entity_rows=entity_rows)

    conn.commit()
    conn.close()
    invalidate_runtime_retrieval_cache(db_path=db_path, scene_id=scene_id)

    return {
        "event_id": event_id,
        "event_type": "dialogue_event",
        "scene_id": scene_id,
        "snapshot_id": snapshot_id,
    }


def process_dialogue_turn(
    db_path: Path,
    scene_id: str,
    user_input: str,
    response_text: str,
    speaking_person_ids: list[str] | None = None,
) -> dict:
    # 1. 获取检索包
    package = build_runtime_retrieval_package_from_db(db_path, scene_id)

    # 2. 记录对话事件
    event_result = record_dialogue_event(
        db_path=db_path,
        scene_id=scene_id,
        user_input=user_input,
        response_text=response_text,
        speaking_person_ids=speaking_person_ids,
    )

    # 3. 推理 patch
    patches = infer_dialogue_patches(
        source_event_id=event_result["event_id"],
        scene_id=scene_id,
        user_input=user_input,
        response_text=response_text,
        speaking_person_ids=speaking_person_ids,
    )

    # 4. 逐个应用
    for patch in patches:
        apply_patch_record(db_path=db_path, patch=patch)

    # 5. 返回结果
    return {
        "retrieval_package": package,
        "event_id": event_result["event_id"],
        "snapshot_id": event_result["snapshot_id"],
        "applied_patch_count": len(patches),
    }
