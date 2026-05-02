import json
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.llm.providers.mock import MockLLMClient
from we_together.services.facet_extraction_service import extract_facets_for_person


def _add_person(db_path, pid, name, persona=None):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(person_id, primary_name, status, persona_summary,
                            confidence, metadata_json, created_at, updated_at)
        VALUES(?, ?, 'active', ?, 0.8, '{}', datetime('now'), datetime('now'))
        """,
        (pid, name, persona),
    )
    conn.commit()
    conn.close()


def _add_event(db_path, eid, person_id, summary):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
                           visibility_level, confidence, is_structured,
                           raw_evidence_refs_json, metadata_json, created_at)
        VALUES(?, 'narration_seed', 'manual', datetime('now'), ?,
               'visible', 0.8, 0, '[]', '{}', datetime('now'))
        """,
        (eid, summary),
    )
    conn.execute(
        "INSERT INTO event_participants(event_id, person_id, participant_role) VALUES(?, ?, 'speaker')",
        (eid, person_id),
    )
    conn.commit()
    conn.close()


def test_extract_facets_writes_via_patch(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_fx", "Fx")
    _add_event(db_path, "evt_fx_1", "person_fx", "做了一周技术分享")
    _add_event(db_path, "evt_fx_2", "person_fx", "周末爬山")

    mock = MockLLMClient(scripted_json=[{
        "facets": [
            {"facet_type": "work", "facet_key": "skill",
             "facet_value": "tech_speaking", "confidence": 0.8, "reason": "evt 1"},
            {"facet_type": "life", "facet_key": "hobby",
             "facet_value": "hiking", "confidence": 0.7, "reason": "evt 2"},
        ]
    }])

    result = extract_facets_for_person(
        db_path=db_path, person_id="person_fx", llm_client=mock,
    )
    assert result["applied_count"] == 2

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT facet_type, facet_value_json, confidence FROM person_facets WHERE person_id = 'person_fx' ORDER BY facet_type"
    ).fetchall()
    conn.close()
    assert len(rows) == 2
    work_value = json.loads(rows[1][1])
    assert work_value["value"] == "tech_speaking"


def test_extract_facets_handles_missing_person(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    import pytest
    with pytest.raises(ValueError):
        extract_facets_for_person(
            db_path=db_path, person_id="person_nope",
            llm_client=MockLLMClient(),
        )


def test_extract_facets_handles_llm_failure(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_failing", "F")

    class Bad:
        provider = "bad"
        def chat(self, *a, **k): raise RuntimeError()
        def chat_json(self, *a, **k): raise RuntimeError("nope")

    result = extract_facets_for_person(
        db_path=db_path, person_id="person_failing", llm_client=Bad(),
    )
    assert "error" in result
    assert result["applied_count"] == 0
