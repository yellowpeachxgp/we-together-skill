"""Phase 35 — 媒体资产落盘 (MM slices)。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def test_media_asset_register_and_dedup(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.media_asset_service import register

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    r1 = register(db, kind="image", content=b"hello", owner_id="p1",
                   visibility="shared", summary="first")
    assert r1["dedup"] is False
    media_id_1 = r1["media_id"]

    # 同 owner 同 content 触发 dedup
    r2 = register(db, kind="image", content=b"hello", owner_id="p1")
    assert r2["dedup"] is True
    assert r2["media_id"] == media_id_1


def test_media_list_by_owner(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.media_asset_service import list_by_owner, register

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    register(db, kind="image", content=b"a", owner_id="p1", summary="a")
    register(db, kind="audio", content=b"b", owner_id="p1", summary="b")
    items = list_by_owner(db, "p1")
    assert len(items) == 2
    assert {it["kind"] for it in items} == {"image", "audio"}


def test_media_list_by_scene(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.media_asset_service import list_by_scene, register

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    register(db, kind="image", content=b"x", owner_id="p1", scene_id="s1")
    register(db, kind="image", content=b"y", owner_id="p2", scene_id="s1")
    register(db, kind="image", content=b"z", owner_id="p3", scene_id="s2")
    s1 = list_by_scene(db, "s1")
    assert len(s1) == 2


def test_media_link_and_filter_visibility(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.media_asset_service import (
        filter_by_visibility, register,
    )

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    r1 = register(db, kind="image", content=b"private-1",
                   owner_id="p1", visibility="private")
    r2 = register(db, kind="image", content=b"shared-1",
                   owner_id="p2", visibility="shared")
    items = [
        {"media_id": r1["media_id"], "visibility": "private", "owner_id": "p1"},
        {"media_id": r2["media_id"], "visibility": "shared", "owner_id": "p2"},
    ]
    visible_to_p1 = filter_by_visibility(items, viewer_id="p1")
    visible_to_p2 = filter_by_visibility(items, viewer_id="p2")
    assert len(visible_to_p1) == 2  # 自己的 private + 共享
    assert len(visible_to_p2) == 1  # 只能看 shared
    assert visible_to_p2[0]["visibility"] == "shared"


def test_ocr_to_memory_end_to_end(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.llm.providers.vision import MockVisionLLMClient
    from we_together.services.media_asset_service import list_media_for_memory
    from we_together.services.ocr_service import ocr_to_memory

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # 先插入一个 person 用于 owner
    import sqlite3
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('p_ocr','P','active',0.8,'{}',"
        "datetime('now'),datetime('now'))"
    )
    c.commit()
    c.close()

    vision = MockVisionLLMClient(scripted_descriptions=["猫咪蹲在地板上"])
    r = ocr_to_memory(
        db, image_bytes=b"cat-bytes", owner_id="p_ocr",
        visibility="shared", vision_client=vision,
    )
    assert r["summary"] == "猫咪蹲在地板上"
    assert r["media_id"].startswith("media_")
    assert r["memory_id"].startswith("mem_ocr_")

    linked = list_media_for_memory(db, r["memory_id"])
    assert len(linked) == 1
    assert linked[0]["media_id"] == r["media_id"]


def test_transcribe_to_event_end_to_end(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.llm.providers.audio import MockAudioTranscriber
    from we_together.services.ocr_service import transcribe_to_event

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    import sqlite3
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('p_asr','P','active',0.8,'{}',"
        "datetime('now'),datetime('now'))"
    )
    c.commit()
    c.close()

    asr = MockAudioTranscriber(scripted_transcripts=["会议讨论了发布日期"])
    r = transcribe_to_event(
        db, audio_bytes=b"audio-bytes", owner_id="p_asr",
        transcriber=asr,
    )
    assert r["transcript"] == "会议讨论了发布日期"
    assert r["event_id"].startswith("evt_audio_")

    import sqlite3
    c = sqlite3.connect(db)
    row = c.execute("SELECT event_type FROM events WHERE event_id=?",
                     (r["event_id"],)).fetchone()
    c.close()
    assert row[0] == "audio_message"


def test_media_embedding_cross_modal():
    """跨模态 mock：同一 dim 下 text vs image 可 cosine 排序。"""
    from we_together.llm.providers.multimodal_embedding import (
        MockMultimodalClient, cross_modal_similarity,
    )
    c = MockMultimodalClient(dim=16)
    q = c.embed_text(["cat"])[0]
    cands = [
        ("img_cat", c.embed_image([b"cat-img"])[0]),
        ("img_dog", c.embed_image([b"dog-img"])[0]),
        ("img_car", c.embed_image([b"car-img"])[0]),
    ]
    top = cross_modal_similarity(q, cands, k=3)
    assert len(top) == 3
    # 顺序保证（不保证哪个第一，但顶部得分 >= 底部）
    assert top[0][1] >= top[-1][1]


def test_multimodal_benchmark_loadable():
    """benchmarks/multimodal_retrieval_groundtruth.json 可 parse"""
    import json
    path = REPO_ROOT / "benchmarks" / "multimodal_retrieval_groundtruth.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["benchmark_name"] == "multimodal_retrieval_v1"
    assert len(data["query_to_images"]) >= 1
