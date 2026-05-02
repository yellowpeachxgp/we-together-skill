"""Phase 45 — 图谱时间 + 自修复 (GT slices)。"""
from __future__ import annotations

import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def test_graph_clock_fallback_without_table():
    """当 db_path=None 或表不存在，必须 fallback 真时间"""
    from we_together.services import graph_clock
    t = graph_clock.now(None)
    assert isinstance(t, datetime)
    # 与真时间偏差 < 2s
    assert abs((datetime.now(UTC) - t).total_seconds()) < 2


def test_graph_clock_migration_0017_installed(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT simulated_now FROM graph_clock WHERE id=1"
    ).fetchone()
    conn.close()
    assert row is not None  # default row 存在，value 默认 NULL


def test_graph_clock_set_and_now(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services import graph_clock
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    target = datetime(2030, 1, 1, tzinfo=UTC)
    graph_clock.set_time(db, target)
    graph_clock.freeze(db)  # 防止自动漂移

    t = graph_clock.now(db)
    assert t.year == 2030
    assert t.month == 1
    assert t.day == 1


def test_graph_clock_advance(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services import graph_clock
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    target = datetime(2026, 1, 1, tzinfo=UTC)
    graph_clock.set_time(db, target)
    graph_clock.freeze(db)

    graph_clock.advance(db, days=7)
    t = graph_clock.now(db)
    assert (t - target).days == 7


def test_graph_clock_clear(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services import graph_clock
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    graph_clock.set_time(db, datetime(2050, 1, 1, tzinfo=UTC))
    graph_clock.freeze(db)
    graph_clock.clear(db)

    t = graph_clock.now(db)
    # clear 后回落到真时间
    assert abs((datetime.now(UTC) - t).total_seconds()) < 2


def test_graph_clock_history_recorded(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services import graph_clock
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    graph_clock.set_time(db, datetime(2027, 6, 15, tzinfo=UTC))
    graph_clock.advance(db, days=3)
    graph_clock.freeze(db)

    conn = sqlite3.connect(db)
    actions = [r[0] for r in conn.execute(
        "SELECT action FROM graph_clock_history ORDER BY history_id"
    ).fetchall()]
    conn.close()
    assert actions == ["set", "advance", "freeze"]


def test_integrity_audit_healthy(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.integrity_audit import full_audit
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    r = full_audit(db)
    assert r["healthy"] is True
    assert r["total_issues"] == 0


def test_integrity_audit_detects_dangling(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.integrity_audit import full_audit
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_audit_1', 'shared_memory', 'test', 0.7, 0.7, 1, 'active',
           '{}', datetime('now'), datetime('now'))"""
    )
    conn.execute(
        "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
        "VALUES('m_audit_1', 'person', 'ghost_person', NULL)"
    )
    conn.commit()
    conn.close()

    r = full_audit(db)
    assert r["healthy"] is False
    assert len(r["dangling_memory_owners"]) == 1
    assert r["dangling_memory_owners"][0]["memory_id"] == "m_audit_1"


def test_integrity_audit_detects_orphan(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.integrity_audit import full_audit
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_orphan_1', 'shared_memory', 'no owner', 0.7, 0.7, 1, 'active',
           '{}', datetime('now'), datetime('now'))"""
    )
    conn.commit()
    conn.close()

    r = full_audit(db)
    assert len(r["orphaned_memories"]) >= 1


def test_self_repair_report_only_does_nothing(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.self_repair import self_repair
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_r1', 'shared_memory', 'x', 0.7, 0.7, 1, 'active',
           '{}', datetime('now'), datetime('now'))"""
    )
    conn.commit()
    conn.close()

    r = self_repair(db, policy="report_only")
    assert r["policy"] == "report_only"
    assert r["actions"] == []

    # 验证没修
    conn = sqlite3.connect(db)
    status = conn.execute(
        "SELECT status FROM memories WHERE memory_id='m_r1'"
    ).fetchone()[0]
    conn.close()
    assert status == "active"


def test_self_repair_auto_marks_orphan_cold(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.self_repair import self_repair
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_r2', 'shared_memory', 'x', 0.7, 0.7, 1, 'active',
           '{}', datetime('now'), datetime('now'))"""
    )
    conn.commit()
    conn.close()

    r = self_repair(db, policy="auto")
    assert r["policy"] == "auto"
    assert any(a["action"] == "mark_memory_cold" for a in r["actions"])

    conn = sqlite3.connect(db)
    status = conn.execute(
        "SELECT status FROM memories WHERE memory_id='m_r2'"
    ).fetchone()[0]
    conn.close()
    assert status == "cold"


def test_self_repair_propose_only(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.self_repair import self_repair
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_r3', 'shared_memory', 'x', 0.7, 0.7, 1, 'active',
           '{}', datetime('now'), datetime('now'))"""
    )
    conn.commit()
    conn.close()

    r = self_repair(db, policy="propose")
    assert r["policy"] == "propose"
    assert r["actions"] == []
    assert any(p["type"] == "mark_memory_cold" for p in r["proposals"])

    # propose 不改数据
    conn = sqlite3.connect(db)
    status = conn.execute(
        "SELECT status FROM memories WHERE memory_id='m_r3'"
    ).fetchone()[0]
    conn.close()
    assert status == "active"


def test_simulate_year_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "simulate_year.py"
    spec = importlib.util.spec_from_file_location("sim_year_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.run_year)
    assert callable(mod.main)


def test_simulate_year_short_run(temp_project_dir):
    """3 天模拟"""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from seed_demo import seed_society_c
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"

    import importlib.util
    p = REPO_ROOT / "scripts" / "simulate_year.py"
    spec = importlib.util.spec_from_file_location("sim_year_t2", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    report = mod.run_year(db, days=3, budget=0)
    assert report["days"] == 3
    assert "sanity" in report
    assert "integrity" in report


def test_fix_graph_cli_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "fix_graph.py"
    spec = importlib.util.spec_from_file_location("fix_graph_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
