import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.llm.providers.mock import MockLLMClient
from we_together.services.fusion_service import fuse_all
from we_together.services.llm_extraction_service import extract_candidates_from_text


def test_extract_with_mock_llm_writes_candidates(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    mock = MockLLMClient(scripted_json=[{
        "identity_candidates": [
            {"display_name": "小王", "confidence": 0.8},
            {"display_name": "小李", "confidence": 0.8},
        ],
        "relation_clues": [
            {
                "participants": ["小王", "小李"],
                "core_type_hint": "friendship",
                "strength_hint": 0.7,
                "confidence": 0.75,
                "summary": "朋友关系",
            }
        ],
        "event_candidates": [
            {
                "event_type": "casual_chat",
                "actor_display_names": ["小王", "小李"],
                "summary": "晚上聊天",
                "confidence": 0.7,
            }
        ],
    }])

    result = extract_candidates_from_text(
        db_path=db_path,
        text="小王和小李是老朋友，昨晚一起聊天。",
        source_name="manual",
        llm_client=mock,
    )

    assert result["identity_candidates"] == 2
    assert result["relation_clues"] == 1
    assert result["event_candidates"] == 1

    conn = sqlite3.connect(db_path)
    idc = conn.execute("SELECT COUNT(*) FROM identity_candidates").fetchone()[0]
    rlc = conn.execute("SELECT COUNT(*) FROM relation_clues").fetchone()[0]
    evc = conn.execute("SELECT COUNT(*) FROM event_candidates").fetchone()[0]
    conn.close()
    assert (idc, rlc, evc) == (2, 1, 1)


def test_extract_then_fuse_creates_graph_objects(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    mock = MockLLMClient(scripted_json=[{
        "identity_candidates": [
            {"display_name": "Alice", "platform": "email", "external_id": "a@a.com", "confidence": 0.9},
            {"display_name": "Bob", "platform": "email", "external_id": "b@a.com", "confidence": 0.9},
        ],
        "relation_clues": [
            {
                "participants": ["Alice", "Bob"],
                "core_type_hint": "colleague",
                "confidence": 0.8,
                "summary": "同事",
            }
        ],
    }])

    extract_candidates_from_text(
        db_path=db_path, text="Alice 和 Bob 是同事。",
        source_name="t", llm_client=mock,
    )

    # 提供一个 event 以便 fuse_relation_clues 挂载
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
                           visibility_level, confidence, is_structured,
                           raw_evidence_refs_json, metadata_json, created_at)
        VALUES('evt_fusion_after_llm', 'narration_seed', 'manual', datetime('now'),
               't', 'visible', 0.8, 0, '[]', '{}', datetime('now'))
        """
    )
    conn.commit()
    conn.close()

    out = fuse_all(db_path, source_event_id="evt_fusion_after_llm")

    assert out["identity"]["fused_count"] == 2
    assert out["relation"]["fused_count"] == 1

    conn = sqlite3.connect(db_path)
    person_count = conn.execute(
        "SELECT COUNT(*) FROM persons WHERE primary_name IN ('Alice', 'Bob')"
    ).fetchone()[0]
    conn.close()
    assert person_count == 2


def test_extract_handles_llm_failure_gracefully(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    class FailingClient:
        provider = "failing"

        def chat(self, *a, **k):
            raise RuntimeError("boom")

        def chat_json(self, *a, **k):
            raise RuntimeError("extract failed")

    result = extract_candidates_from_text(
        db_path=db_path, text="x", source_name="t",
        llm_client=FailingClient(),
    )
    assert "error" in result
    assert result["identity_candidates"] == 0
