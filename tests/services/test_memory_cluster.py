import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from we_together.db.bootstrap import bootstrap_project  # noqa: E402
from we_together.services.memory_cluster_service import cluster_memories  # noqa: E402


def _insert_mem(db_path, mid, mtype, owners, summary=""):
    c = sqlite3.connect(db_path)
    c.execute(
        """INSERT INTO memories(
            memory_id, memory_type, summary, relevance_score, confidence,
            is_shared, status, metadata_json, created_at, updated_at
        ) VALUES(?,?,?,0.7,0.7,1,'active','{}',datetime('now'),datetime('now'))""",
        (mid, mtype, summary or mid),
    )
    for o in owners:
        c.execute(
            """INSERT OR IGNORE INTO persons(person_id, primary_name, status, confidence,
               metadata_json, created_at, updated_at)
               VALUES(?,?,'active',0.8,'{}',datetime('now'),datetime('now'))""",
            (o, o),
        )
        c.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, NULL)",
            (mid, o),
        )
    c.commit()
    c.close()


def test_cluster_same_type_overlapping_owners(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _insert_mem(db_path, "m1", "shared_memory", ["a", "b"])
    _insert_mem(db_path, "m2", "shared_memory", ["a", "b", "c"])
    _insert_mem(db_path, "m3", "shared_memory", ["x", "y"])

    clusters = cluster_memories(db_path)
    # m1,m2 应成一个 cluster（owners 重叠度 >= 0.5）
    by_id = {c["cluster_id"]: c for c in clusters}
    found = False
    for c in clusters:
        if set(c["memory_ids"]) == {"m1", "m2"}:
            found = True
            assert c["memory_type"] == "shared_memory"
            assert set(c["owner_ids"]) >= {"a", "b"}
    assert found, f"expected m1+m2 cluster, got {by_id}"


def test_cluster_respects_min_size(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _insert_mem(db_path, "solo", "individual_memory", ["z"])

    clusters = cluster_memories(db_path, min_cluster_size=2)
    ids = {mid for c in clusters for mid in c["memory_ids"]}
    assert "solo" not in ids


def test_cluster_different_types_not_merged(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _insert_mem(db_path, "s1", "shared_memory", ["a", "b"])
    _insert_mem(db_path, "i1", "individual_memory", ["a", "b"])

    clusters = cluster_memories(db_path, min_cluster_size=1)
    for c in clusters:
        types = {m for m in c["memory_ids"]}
        # 不同类型不能合并：s1 与 i1 不能在同一个 cluster
        assert not ({"s1", "i1"} <= set(c["memory_ids"]))
