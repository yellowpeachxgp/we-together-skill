"""Phase 52 — AI Agent 元能力 (AG slices)。"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _seed_person(db: Path, pid: str) -> str:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO persons(person_id, primary_name, status, confidence, "
            "metadata_json, created_at, updated_at) VALUES(?, ?, 'active', 0.9, "
            "'{}', datetime('now'), datetime('now'))",
            (pid, pid),
        )
        conn.commit()
    finally:
        conn.close()
    return pid


def _seed_memory(db: Path, mid: str, owner: str, summary: str) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'individual_memory', ?, 0.7, 0.7, 0, 'active', '{}',
               datetime('now'), datetime('now'))""",
            (mid, summary),
        )
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, NULL)", (mid, owner),
        )
        conn.commit()
    finally:
        conn.close()


def test_migration_0021_installed(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "agent_drives" in names
    assert "autonomous_actions" in names


def test_detect_drives_keywords():
    from we_together.services.autonomous_agent import _detect_drives_from_text
    hits = dict(_detect_drives_from_text("我很想念她，想找她聊聊"))
    assert "connection" in hits
    assert hits["connection"] > 0

    hits2 = dict(_detect_drives_from_text("感觉好累，想休息"))
    assert "rest" in hits2

    hits3 = dict(_detect_drives_from_text("Hello world"))
    assert hits3 == {}


def test_compute_drives_from_memories(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.autonomous_agent import compute_drives
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pid = _seed_person(db, "p_drive_1")
    _seed_memory(db, "m_d1", pid, "我很想念老朋友，想联系他")
    _seed_memory(db, "m_d2", pid, "好累啊，想休息一下")

    drives = compute_drives(db, pid, lookback_days=30)
    types = {d.drive_type for d in drives}
    assert "connection" in types or "rest" in types
    # 至少每个 drive 有来源 memory
    for d in drives:
        assert len(d.source_memory_ids) >= 1


def test_persist_and_list_drives(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.autonomous_agent import (
        compute_drives, persist_drives,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pid = _seed_person(db, "p_drive_2")
    _seed_memory(db, "m_d3", pid, "好奇对方为什么不回消息")

    drives = compute_drives(db, pid)
    n = persist_drives(db, drives)
    assert n >= 1

    conn = sqlite3.connect(db)
    cnt = conn.execute(
        "SELECT COUNT(*) FROM agent_drives WHERE person_id=?", (pid,),
    ).fetchone()[0]
    conn.close()
    assert cnt >= 1


def test_decide_action_below_threshold():
    from we_together.services.autonomous_agent import Drive, decide_action
    d = Drive(drive_id="x", person_id="p", drive_type="connection", intensity=0.2)
    intent = decide_action([d], threshold=0.5)
    assert intent is None


def test_decide_action_returns_intent():
    from we_together.services.autonomous_agent import Drive, decide_action
    d = Drive(drive_id="x", person_id="p", drive_type="connection", intensity=0.9)
    intent = decide_action([d])
    assert intent is not None
    assert intent.action_type == "reach_out"
    assert intent.drive_id == "x"


def test_record_autonomous_action_requires_source(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.autonomous_agent import record_autonomous_action
    import pytest
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # 不变式 #27: 必须有 drive / memory / trace 之一
    with pytest.raises(ValueError, match="不变式 #27"):
        record_autonomous_action(db, person_id="p", action_type="reach_out")


def test_record_autonomous_action_with_drive(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.autonomous_agent import (
        record_autonomous_action, list_autonomous_actions,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_person(db, "p_aa")
    aid = record_autonomous_action(
        db, person_id="p_aa", action_type="reflect",
        triggered_by_drive_id="drive_xxx",
        rationale="testing",
    )
    assert aid > 0
    actions = list_autonomous_actions(db, "p_aa")
    assert actions[0]["action_type"] == "reflect"
    assert actions[0]["triggered_by_drive_id"] == "drive_xxx"


def test_dream_cycle_generates_insight(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.dream_cycle import run_dream_cycle
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    pid = _seed_person(db, "p_dream_1")
    for i in range(5):
        _seed_memory(db, f"m_cluster_{i}", pid, f"主题事件 #{i}")

    r = run_dream_cycle(
        db, min_cluster_size=3, lookback_days=30,
        archive_low_relevance=False,
    )
    assert r["insight_seeds"] >= 1
    assert len(r["insights_created"]) >= 1

    conn = sqlite3.connect(db)
    insight_count = conn.execute(
        "SELECT COUNT(*) FROM memories WHERE memory_type='insight'"
    ).fetchone()[0]
    conn.close()
    assert insight_count >= 1


def test_insight_retains_source_memory_ids(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.dream_cycle import run_dream_cycle
    import json as _json
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pid = _seed_person(db, "p_dream_2")
    for i in range(4):
        _seed_memory(db, f"m_src_{i}", pid, f"事件 {i}")

    r = run_dream_cycle(
        db, min_cluster_size=3, archive_low_relevance=False,
    )
    if not r["insights_created"]:
        import pytest
        pytest.skip("no insight created")

    insight_id = r["insights_created"][0]
    conn = sqlite3.connect(db)
    meta = conn.execute(
        "SELECT metadata_json FROM memories WHERE memory_id=?", (insight_id,),
    ).fetchone()[0]
    conn.close()
    meta_d = _json.loads(meta)
    assert "source_memory_ids" in meta_d
    assert len(meta_d["source_memory_ids"]) >= 3


def test_dream_cycle_cli_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "dream_cycle.py"
    spec = importlib.util.spec_from_file_location("dream_cli_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
