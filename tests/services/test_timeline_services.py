import sqlite3
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from we_together.db.bootstrap import bootstrap_project
from we_together.llm.providers.mock import MockLLMClient
from we_together.services.event_causality_service import (
    infer_event_causality,
    list_causality,
)
from we_together.services.persona_drift_service import drift_personas
from we_together.services.persona_history_service import (
    query_as_of,
    query_history,
    record_persona_change,
)
from we_together.services.relation_history_service import (
    get_relation_strength_series,
    list_relations_with_changes,
)


def _insert_person(db_path, pid, name):
    c = sqlite3.connect(db_path)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) "
        "VALUES(?,?,'active',0.8,'{}',datetime('now'),datetime('now'))",
        (pid, name),
    )
    c.commit(); c.close()


def test_persona_history_insert_and_query(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    _insert_person(db, "p1", "A")

    h1 = record_persona_change(db, person_id="p1", persona_summary="old",
                                source_reason="init")
    time.sleep(0.01)
    h2 = record_persona_change(db, person_id="p1", persona_summary="new",
                                source_reason="drift")

    hist = query_history(db, "p1")
    assert len(hist) == 2
    # 最新在前
    assert hist[0]["persona_summary"] == "new"
    assert hist[0]["valid_to"] is None
    assert hist[1]["valid_to"] is not None
    assert h1 != h2


def test_persona_history_as_of(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    _insert_person(db, "p2", "B")

    record_persona_change(db, person_id="p2", persona_summary="v1")
    # 等一点点让时间戳分开
    time.sleep(0.01)
    mid = datetime.now(UTC).isoformat()
    time.sleep(0.01)
    record_persona_change(db, person_id="p2", persona_summary="v2")

    # as_of 在 v1 时间段内 → v1
    row = query_as_of(db, "p2", mid)
    assert row is not None
    assert row["persona_summary"] == "v1"

    # as_of 在 v2 之后 → v2
    future = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    row2 = query_as_of(db, "p2", future)
    assert row2["persona_summary"] == "v2"


def test_persona_drift_writes_history(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    # 准备：一个 person + 若干 events
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, persona_summary, "
        "confidence, metadata_json, created_at, updated_at) "
        "VALUES('p3','C','active','old',0.8,'{}',datetime('now'),datetime('now'))"
    )
    for i in range(4):
        eid = f"evt_tlhist_{i}"
        c.execute(
            """INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
               visibility_level, confidence, is_structured, raw_evidence_refs_json,
               metadata_json, created_at) VALUES(?,'dialogue_event','m',
               datetime('now'), ?, 'visible',0.8,0,'[]','{}',datetime('now'))""",
            (eid, f"discussion {i}"),
        )
        c.execute(
            "INSERT INTO event_participants(event_id, person_id, participant_role) "
            "VALUES(?, 'p3', 'speaker')", (eid,),
        )
    c.commit(); c.close()

    llm = MockLLMClient(scripted_json=[{"persona_summary": "NEW PERSONA",
                                         "style_summary": "calm"}])
    result = drift_personas(db, window_days=30, min_events=3, llm_client=llm)
    assert result["drifted_count"] == 1

    hist = query_history(db, "p3")
    assert len(hist) >= 1
    assert hist[0]["persona_summary"] == "NEW PERSONA"


# --- relation_history ---

def test_list_relations_with_changes(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    for i in range(3):
        c.execute(
            """INSERT INTO patches(patch_id, source_event_id, target_type, target_id,
               operation, payload_json, confidence, reason, status, applied_at,
               created_at) VALUES(?, 'src', 'relation', 'rel_x', 'update_entity',
               '{"strength": 0.5}', 0.5, 'r', 'applied', datetime('now'),
               datetime('now'))""",
            (f"pt_{i}",),
        )
    c.commit(); c.close()
    top = list_relations_with_changes(db, limit=10)
    assert any(r["relation_id"] == "rel_x" for r in top)


def test_strength_series_bucketed(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    c.execute(
        """INSERT INTO patches(patch_id, source_event_id, target_type, target_id,
           operation, payload_json, confidence, reason, status, applied_at,
           created_at) VALUES('pA','s','relation','rel_y','update_entity',
           '{"strength": 0.6}',0.6,'r','applied','2025-01-01T00:00:00+00:00',
           datetime('now'))"""
    )
    c.commit(); c.close()
    s = get_relation_strength_series(db, "rel_y", bucket="month")
    assert len(s) >= 1
    assert s[0]["strength"] == 0.6


# --- event_causality ---

def test_event_causality_inserts_edges(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    for i, s in enumerate(["吃饭", "散步"]):
        eid = f"ec_evt_{i}"
        c.execute(
            """INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
               visibility_level, confidence, is_structured, raw_evidence_refs_json,
               metadata_json, created_at) VALUES(?,'dialogue_event','m',
               datetime('now'), ?, 'visible',0.8,0,'[]','{}',datetime('now'))""",
            (eid, s),
        )
    c.commit(); c.close()

    llm = MockLLMClient(scripted_json=[{"edges": [
        {"cause": "ec_evt_0", "effect": "ec_evt_1", "reason": "吃完散步",
         "confidence": 0.8},
    ]}])
    result = infer_event_causality(db, llm_client=llm)
    assert result["created_count"] == 1
    edges = list_causality(db)
    assert len(edges) == 1
    assert edges[0]["cause"] == "ec_evt_0"
