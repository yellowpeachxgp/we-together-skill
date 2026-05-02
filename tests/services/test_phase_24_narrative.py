import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.db.bootstrap import bootstrap_project  # noqa: E402
from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.services.associative_recall import associate_memories  # noqa: E402
from we_together.services.graph_analytics import (  # noqa: E402
    compute_degree_centrality,
    compute_group_density,
    full_report,
    identify_isolated_persons,
)
from we_together.services.narrative_service import (  # noqa: E402
    aggregate_narrative_arcs,
    list_arcs,
)
from we_together.services.perceived_memory_service import (  # noqa: E402
    query_memories_by_perspective,
    write_perceived_memory,
)


# --- ND-1 narrative ---

def test_narrative_aggregate_writes_arcs(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    events_ids = [f"evt_auto_{i}" for i in range(3)]
    c = sqlite3.connect(db)
    for i, eid in enumerate(events_ids):
        c.execute(
            """INSERT INTO events(event_id, event_type, source_type, timestamp,
               summary, visibility_level, confidence, is_structured,
               raw_evidence_refs_json, metadata_json, created_at) VALUES(?,
               'dialogue_event', 'm', datetime('now', '-'||?||' days'), ?,
               'visible', 0.8, 0, '[]', '{}', datetime('now'))""",
            (eid, i, f"事件 {i}"),
        )
    c.commit(); c.close()

    llm = MockLLMClient(scripted_json=[{
        "arcs": [
            {"title": "第一章", "theme": "开场", "summary": "三件事发生",
             "event_ids": events_ids},
        ],
    }])
    r = aggregate_narrative_arcs(db, llm_client=llm)
    assert r["arc_count"] == 1

    arcs = list_arcs(db)
    assert len(arcs) == 1
    assert arcs[0]["title"] == "第一章"
    assert len(arcs[0]["event_ids"]) == 3


def test_narrative_aggregate_no_events(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    r = aggregate_narrative_arcs(db, llm_client=MockLLMClient())
    assert r["arc_count"] == 0


# --- ND-2 perceived memory ---

def test_perceived_memory_write_and_query(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) "
        "VALUES('p_per','P','active',0.8,'{}',datetime('now'),datetime('now'))"
    )
    c.commit(); c.close()

    mid = write_perceived_memory(
        db, perspective_person_id="p_per",
        summary="我觉得这件事有点奇怪",
    )
    rows = query_memories_by_perspective(db, person_id="p_per")
    assert any(r["memory_id"] == mid and r["perspective_person_id"] == "p_per"
                for r in rows)


def test_perceived_memory_include_collective(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) "
        "VALUES('p_a','A','active',0.8,'{}',datetime('now'),datetime('now'))"
    )
    # 一条集体 memory（perspective 为 NULL）
    c.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_coll','shared_memory','集体记忆',0.7,0.7,1,'active','{}',
           datetime('now'),datetime('now'))"""
    )
    c.commit(); c.close()
    write_perceived_memory(db, perspective_person_id="p_a", summary="我的视角")
    rows = query_memories_by_perspective(db, person_id="p_a",
                                           include_collective=True)
    memory_ids = [r["memory_id"] for r in rows]
    assert "m_coll" in memory_ids
    only_perspective = query_memories_by_perspective(db, person_id="p_a",
                                                       include_collective=False)
    assert all(r["perspective_person_id"] == "p_a" for r in only_perspective)


# --- ND-5 analytics ---

def test_degree_centrality(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    r = compute_degree_centrality(db)
    assert len(r) == 8
    # Alice 作为 society_c 中心应排前列
    names = {x["primary_name"]: x["degree"] for x in r}
    assert names["Alice"] >= 1


def test_group_density(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    r = compute_group_density(db)
    # society_c 无 group 的话应为空
    assert isinstance(r, list)


def test_isolated_persons(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    r = identify_isolated_persons(db, window_days=7)
    # society_c 刚 seed，events 都在 now，无人孤立
    assert isinstance(r, list)


def test_full_report(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    r = full_report(db)
    assert "degree" in r and "group_density" in r and "isolated_persons" in r


# --- ND-3 associative recall ---

def test_associative_recall(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    for i, s in enumerate(["工作会议", "家庭晚餐", "深夜加班"]):
        c.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, 0.8, 0.7, 1, 'active', '{}',
               datetime('now'), datetime('now'))""",
            (f"m_assoc_{i}", s),
        )
    c.commit(); c.close()

    llm = MockLLMClient(scripted_json=[{"associated": ["m_assoc_0", "m_assoc_2"]}])
    r = associate_memories(db, seed_text="工作相关", llm_client=llm)
    assert set(r["associated"]) == {"m_assoc_0", "m_assoc_2"}
    assert r["candidate_count"] == 3
