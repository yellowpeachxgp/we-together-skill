import json
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.importers.image_importer import import_image
from we_together.importers.social_importer import import_social_dump
from we_together.llm.providers.vision import MockVisionLLMClient
from we_together.services.evidence_dedup_service import (
    compute_evidence_hash,
    is_duplicate,
    register_evidence_hash,
)


def test_image_importer_uses_vision_client(tmp_path):
    img = tmp_path / "a.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0 fake jpeg")
    vc = MockVisionLLMClient(scripted_descriptions=["两人在咖啡馆交谈"])
    result = import_image(img, vc)
    assert result["description"] == "两人在咖啡馆交谈"
    assert len(result["event_candidates"]) == 1
    assert result["event_candidates"][0]["event_type"] == "image_event"


def test_social_importer_parses_json_dump(tmp_path):
    dump = tmp_path / "social.json"
    dump.write_text(json.dumps({
        "platform": "x",
        "owner_handle": "me",
        "posts": [
            {"id": "p1", "text": "@alice hi", "created_at": "2024-01-01",
             "mentions": ["alice"]},
        ],
        "following": [{"handle": "alice"}, {"handle": "bob"}],
        "followers": [],
    }))
    result = import_social_dump(dump)
    names = {c["display_name"] for c in result["identity_candidates"]}
    assert "alice" in names and "bob" in names
    assert result["event_candidates"][0]["event_type"] == "social_post"


def test_evidence_hash_deduplication(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    h = compute_evidence_hash("hello world", source_name="fx")

    assert not is_duplicate(db_path, h)
    register_evidence_hash(db_path, h, "ev_1", datetime.now(UTC).isoformat())
    assert is_duplicate(db_path, h)

    # 第二次 register 应幂等
    register_evidence_hash(db_path, h, "ev_1", datetime.now(UTC).isoformat())
    assert is_duplicate(db_path, h)

    # 不同内容不重复
    h2 = compute_evidence_hash("other", source_name="fx")
    assert not is_duplicate(db_path, h2)
