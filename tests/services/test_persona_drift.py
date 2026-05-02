import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.llm.providers.mock import MockLLMClient
from we_together.services.persona_drift_service import drift_personas


def _seed_person_with_events(db_path, pid, name, persona, events_with_offsets):
    c = sqlite3.connect(db_path)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, persona_summary, "
        "style_summary, confidence, metadata_json, created_at, updated_at) "
        "VALUES(?,?,'active',?,NULL,0.8,'{}',datetime('now'),datetime('now'))",
        (pid, name, persona),
    )
    now = datetime.now(UTC)
    for i, (summary, off) in enumerate(events_with_offsets):
        eid = f"evt_{pid}_{i}"
        ts = (now - timedelta(days=off)).isoformat()
        c.execute(
            """INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
               visibility_level, confidence, is_structured, raw_evidence_refs_json,
               metadata_json, created_at) VALUES(?,'dialogue_event','manual',?,?,
               'visible',0.8,0,'[]','{}',datetime('now'))""",
            (eid, ts, summary),
        )
        c.execute(
            "INSERT INTO event_participants(event_id, person_id, participant_role) "
            "VALUES(?, ?, 'speaker')",
            (eid, pid),
        )
    c.commit()
    c.close()


def test_drift_updates_persona_when_enough_events(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_person_with_events(
        db_path, "p_drift", "Drifty", "旧画像",
        [("开会讨论架构", 5), ("code review", 3), ("和 Bob 结对编程", 1), ("深夜加班", 2)],
    )

    llm = MockLLMClient(scripted_json=[{"persona_summary": "投入架构与代码评审的工程师",
                                        "style_summary": "专注"}])
    result = drift_personas(db_path, window_days=30, min_events=3, llm_client=llm)

    assert result["drifted_count"] == 1
    row = sqlite3.connect(db_path).execute(
        "SELECT persona_summary, style_summary FROM persons WHERE person_id = 'p_drift'"
    ).fetchone()
    assert row[0] == "投入架构与代码评审的工程师"
    assert row[1] == "专注"


def test_drift_skips_when_not_enough_events(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_person_with_events(db_path, "p_quiet", "Quiet", "原样", [("单次 event", 2)])

    result = drift_personas(db_path, window_days=30, min_events=3,
                             llm_client=MockLLMClient())
    assert result["drifted_count"] == 0
