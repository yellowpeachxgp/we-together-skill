"""Phase 40 — 神经网格式激活 (NM slices)。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def test_migration_0016_installed(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    import sqlite3
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='activation_traces'"
    ).fetchone()
    conn.close()
    assert row is not None


def test_record_and_recent(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record, recent_traces
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    tid = record(
        db,
        from_entity_type="person", from_entity_id="p1",
        to_entity_type="person", to_entity_id="p2",
        weight=0.8, trace_type="relation_traversal",
        scene_id="scene_x",
    )
    assert tid > 0
    r = recent_traces(db, limit=5)
    assert len(r) == 1
    assert r[0]["from_entity_id"] == "p1"
    assert r[0]["to_entity_id"] == "p2"


def test_count_by_pair(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record, count_by_pair
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    for _ in range(3):
        record(
            db, from_entity_type="person", from_entity_id="p1",
            to_entity_type="person", to_entity_id="p2",
        )
    record(
        db, from_entity_type="person", from_entity_id="p1",
        to_entity_type="person", to_entity_id="p3",
    )
    assert count_by_pair(db, from_entity_id="p1", to_entity_id="p2") == 3
    assert count_by_pair(db, from_entity_id="p1", to_entity_id="p3") == 1
    assert count_by_pair(db, from_entity_id="p3", to_entity_id="p1") == 0


def test_query_path_2_hop(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record, query_path
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # p1 -> p2 -> p3
    record(db, from_entity_type="person", from_entity_id="p1",
           to_entity_type="person", to_entity_id="p2")
    record(db, from_entity_type="person", from_entity_id="p2",
           to_entity_type="person", to_entity_id="p3")
    paths = query_path(db, from_entity_id="p1", to_entity_id="p3", max_hops=3)
    assert len(paths) == 1
    path = paths[0]
    assert path[0]["from"] == "p1" and path[0]["to"] == "p2"
    assert path[1]["from"] == "p2" and path[1]["to"] == "p3"


def test_multi_hop_activation_decay(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import (
        record, multi_hop_activation,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    record(db, from_entity_type="person", from_entity_id="p1",
           to_entity_type="person", to_entity_id="p2", weight=1.0)
    record(db, from_entity_type="person", from_entity_id="p2",
           to_entity_type="person", to_entity_id="p3", weight=1.0)

    m = multi_hop_activation(db, start_entity_id="p1", max_hops=3, decay=0.5)
    assert "p1" in m and m["p1"] == 1.0
    # p2 = 1 * 1.0 * 0.5 = 0.5
    assert abs(m["p2"] - 0.5) < 1e-6
    # p3 = 0.5 * 1.0 * 0.5 = 0.25
    assert abs(m["p3"] - 0.25) < 1e-6


def test_apply_plasticity_updates_relation(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record, apply_plasticity
    import sqlite3

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # seed: 两个 person + 一条 relation + entity_links
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pA','A','active',0.8,'{}',"
        "datetime('now'),datetime('now'))"
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pB','B','active',0.8,'{}',"
        "datetime('now'),datetime('now'))"
    )
    conn.execute(
        """INSERT INTO relations(relation_id, core_type, status, strength,
           confidence, metadata_json, created_at, updated_at)
           VALUES('rAB','friendship','active',0.3,0.7,'{}',
           datetime('now'),datetime('now'))"""
    )
    for pid in ("pA", "pB"):
        conn.execute(
            "INSERT INTO entity_links(from_type, from_id, relation_type, "
            "to_type, to_id, weight, metadata_json) "
            "VALUES('relation','rAB','participant','person',?, 1.0, '{}')",
            (pid,),
        )
    conn.commit()
    conn.close()

    # 5 次激活 pA→pB
    for _ in range(5):
        record(
            db, from_entity_type="person", from_entity_id="pA",
            to_entity_type="person", to_entity_id="pB",
            trace_type="scene_participation",
        )

    r = apply_plasticity(db, min_count=3, strength_delta=0.05, since_days=30)
    assert r["updated"] == 1
    assert r["details"][0]["relation_id"] == "rAB"
    assert r["details"][0]["new_strength"] > 0.3


def test_plasticity_no_relation_no_change(temp_project_with_migrations):
    """不存在 relation 时，激活不应凭空造 relation"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record, apply_plasticity
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    for _ in range(10):
        record(db, from_entity_type="person", from_entity_id="pX",
               to_entity_type="person", to_entity_id="pY")
    r = apply_plasticity(db, min_count=3)
    assert r["updated"] == 0


def test_decay_traces(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record, decay_traces
    import sqlite3
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    record(db, from_entity_type="person", from_entity_id="p1",
           to_entity_type="person", to_entity_id="p2")

    # 人工老化一条
    conn = sqlite3.connect(db)
    conn.execute(
        "UPDATE activation_traces SET activated_at = datetime('now', '-120 days') "
        "WHERE from_entity_id='p1'"
    )
    conn.commit()
    conn.close()

    n = decay_traces(db, age_days=90)
    assert n == 1


def test_convergence_stable_weights(temp_project_with_migrations):
    """连续激活 30 次后 strength 不超过 max_strength"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record, apply_plasticity
    import sqlite3
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    for pid in ("pC", "pD"):
        conn.execute(
            "INSERT INTO persons(person_id, primary_name, status, confidence, "
            "metadata_json, created_at, updated_at) VALUES(?, ?, 'active', 0.8, "
            "'{}', datetime('now'), datetime('now'))",
            (pid, pid.upper()),
        )
    conn.execute(
        """INSERT INTO relations(relation_id, core_type, status, strength,
           confidence, metadata_json, created_at, updated_at)
           VALUES('rCD','friendship','active',0.5,0.7,'{}',
           datetime('now'),datetime('now'))"""
    )
    for pid in ("pC", "pD"):
        conn.execute(
            "INSERT INTO entity_links(from_type, from_id, relation_type, "
            "to_type, to_id, weight, metadata_json) "
            "VALUES('relation','rCD','participant','person',?, 1.0, '{}')",
            (pid,),
        )
    conn.commit()
    conn.close()

    for _ in range(30):
        record(db, from_entity_type="person", from_entity_id="pC",
               to_entity_type="person", to_entity_id="pD")
    # 多次 apply_plasticity
    for _ in range(10):
        apply_plasticity(db, min_count=3, strength_delta=0.05, max_strength=1.0)

    conn = sqlite3.connect(db)
    s = conn.execute(
        "SELECT strength FROM relations WHERE relation_id='rCD'"
    ).fetchone()[0]
    conn.close()
    # 应收敛到 max_strength=1.0 附近
    assert 0.9 <= s <= 1.0


def test_activation_path_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "activation_path.py"
    spec = importlib.util.spec_from_file_location("act_path_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
