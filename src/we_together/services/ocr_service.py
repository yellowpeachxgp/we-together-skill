"""ocr_service / audio_transcribe_service（Phase 35 MM-4/5/6/7）。

把 vision / audio provider 封装到图谱链路：
- ocr_to_memory(db, image_bytes, owner_id, scene_id, vision_client) → {media_id, memory_id}
- transcribe_to_event(db, audio_bytes, owner_id, scene_id, transcriber) → {media_id, event_id}

产生的 memory/event 走图谱通用路径（非 patch，这里是直接 INSERT，因为媒体摄入
是一个单一 importer 行为；下一步要改造成 importer 形态时可走 patch）。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from we_together.services import media_asset_service


def ocr_to_memory(
    db_path: Path, *,
    image_bytes: bytes,
    owner_id: str,
    scene_id: str | None = None,
    visibility: str = "shared",
    vision_client,
    prompt: str = "",
) -> dict:
    description = vision_client.describe_image(image_bytes, prompt=prompt)

    reg = media_asset_service.register(
        db_path, kind="image", content=image_bytes,
        owner_id=owner_id, visibility=visibility, scene_id=scene_id,
        summary=description, mime_type="image/jpeg",
    )
    media_id = reg["media_id"]

    mem_id = f"mem_ocr_{uuid.uuid4().hex[:10]}"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, 0.6, 0.6, ?, 'active', ?,
               datetime('now'), datetime('now'))""",
            (mem_id, description, 1 if visibility != "private" else 0,
             json.dumps({"source": "ocr", "media_id": media_id})),
        )
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, NULL)",
            (mem_id, owner_id),
        )
        conn.commit()
    finally:
        conn.close()

    media_asset_service.link_to_memory(db_path, media_id, mem_id)
    return {"media_id": media_id, "memory_id": mem_id, "summary": description}


def transcribe_to_event(
    db_path: Path, *,
    audio_bytes: bytes,
    owner_id: str,
    scene_id: str | None = None,
    visibility: str = "shared",
    transcriber,
    language: str | None = None,
) -> dict:
    text = transcriber.transcribe(audio_bytes, language=language)

    reg = media_asset_service.register(
        db_path, kind="audio", content=audio_bytes,
        owner_id=owner_id, visibility=visibility, scene_id=scene_id,
        summary=text, mime_type="audio/mpeg",
    )
    media_id = reg["media_id"]

    ev_id = f"evt_audio_{uuid.uuid4().hex[:10]}"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
               visibility_level, confidence, is_structured, raw_evidence_refs_json,
               metadata_json, created_at)
               VALUES(?, 'audio_message', 'audio_importer', datetime('now'),
               ?, ?, 0.6, 1, '[]', ?, datetime('now'))""",
            (ev_id, text, visibility,
             json.dumps({"source": "audio_transcribe", "media_id": media_id})),
        )
        if scene_id:
            conn.execute(
                "UPDATE events SET scene_id=? WHERE event_id=?",
                (scene_id, ev_id),
            )
        conn.commit()
    finally:
        conn.close()

    media_asset_service.link_to_event(db_path, media_id, ev_id)
    return {"media_id": media_id, "event_id": ev_id, "transcript": text}
