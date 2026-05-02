import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from we_together.db.bootstrap import bootstrap_project  # noqa: E402
from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.services.memory_condenser_service import (  # noqa: E402
    condense_memory_clusters,
)


def _seed_cluster(db_path, ids, mtype, owners):
    c = sqlite3.connect(db_path)
    for pid in owners:
        c.execute(
            "INSERT OR IGNORE INTO persons(person_id, primary_name, status, confidence, "
            "metadata_json, created_at, updated_at) VALUES(?,?,'active',0.8,'{}',"
            "datetime('now'),datetime('now'))",
            (pid, pid),
        )
    for mid in ids:
        c.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score, confidence,
               is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?,?,?,0.7,0.7,1,'active','{}',datetime('now'),datetime('now'))""",
            (mid, mtype, f"原始 {mid}"),
        )
        for o in owners:
            c.execute(
                "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
                "VALUES(?, 'person', ?, NULL)",
                (mid, o),
            )
    c.commit()
    c.close()


def test_condense_writes_summary_memory_with_refs(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_cluster(db_path, ["m1", "m2", "m3"], "shared_memory", ["a", "b"])

    llm = MockLLMClient(scripted_json=[{"summary": "三人共同的工作记忆"}])
    result = condense_memory_clusters(db_path, llm_client=llm)

    assert result["condensed_count"] == 1
    created = result["created"][0]
    assert set(created["refs"]) == {"m1", "m2", "m3"}
    assert created["summary"] == "三人共同的工作记忆"

    c = sqlite3.connect(db_path)
    row = c.execute(
        "SELECT memory_type, summary, metadata_json FROM memories WHERE memory_id = ?",
        (created["memory_id"],),
    ).fetchone()
    assert row[0] == "condensed_memory"
    assert row[1] == "三人共同的工作记忆"
    meta = json.loads(row[2])
    assert set(meta["condensed_from"]) == {"m1", "m2", "m3"}

    owners = c.execute(
        "SELECT owner_id FROM memory_owners WHERE memory_id = ?",
        (created["memory_id"],),
    ).fetchall()
    assert {o[0] for o in owners} == {"a", "b"}
    c.close()


def test_condense_no_clusters_is_noop(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_cluster(db_path, ["solo"], "individual_memory", ["z"])

    result = condense_memory_clusters(db_path, llm_client=MockLLMClient())
    assert result["condensed_count"] == 0
