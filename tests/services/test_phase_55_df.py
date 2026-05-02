"""Phase 55 — 差异化能力双击 (DF slices)。"""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


# --- working_memory ---

def test_working_memory_add_and_snapshot():
    from we_together.services.working_memory import (
        WorkingMemoryBuffer, clear_all,
    )
    clear_all()
    buf = WorkingMemoryBuffer(scene_id="s1", capacity=10)
    buf.add_note("刚想起 Alice 昨天的话", kind="recall",
                  weight=0.8, source_refs=["m_1"])
    buf.add_note("当前 drive: connection", kind="drive", weight=0.9)
    snap = buf.snapshot()
    assert len(snap) == 2
    assert snap[0]["content"]
    assert "expires_in_seconds" in snap[0]


def test_working_memory_capacity_prune():
    from we_together.services.working_memory import WorkingMemoryBuffer
    buf = WorkingMemoryBuffer(scene_id="s2", capacity=3)
    for i in range(5):
        buf.add_note(f"note {i}", weight=0.1 * i)
    assert buf.size() == 3


def test_working_memory_ttl_expiry():
    from we_together.services.working_memory import WorkingMemoryBuffer
    buf = WorkingMemoryBuffer(scene_id="s3")
    buf.add_note("短命", ttl_seconds=0.05)
    time.sleep(0.1)
    snap = buf.snapshot()
    # 过期被 prune
    assert len(snap) == 0


def test_get_buffer_creates_per_scene():
    from we_together.services.working_memory import (
        clear_all, get_buffer,
    )
    clear_all()
    b1 = get_buffer("scene_a")
    b2 = get_buffer("scene_b")
    b1_again = get_buffer("scene_a")
    assert b1 is b1_again
    assert b1 is not b2


def test_snapshot_all():
    from we_together.services.working_memory import (
        clear_all, get_buffer, snapshot_all,
    )
    clear_all()
    b = get_buffer("scene_snap")
    b.add_note("x")
    all_snap = snapshot_all()
    assert "scene_snap" in all_snap
    assert len(all_snap["scene_snap"]) == 1


# --- derivation rebuild (不变式 #28) ---

def _seed_person(db: Path, pid: str) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO persons(person_id, primary_name, status, confidence, "
            "metadata_json, created_at, updated_at) VALUES(?, ?, 'active', 0.9, "
            "'{}', datetime('now'), datetime('now'))", (pid, pid),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_memory(db: Path, mid: str, owner: str, summary: str) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'individual_memory', ?, 0.7, 0.7, 0, 'active', '{}',
               datetime('now'), datetime('now'))""", (mid, summary),
        )
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, NULL)", (mid, owner),
        )
        conn.commit()
    finally:
        conn.close()


def test_get_insight_sources_returns_source_memory_ids(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.dream_cycle import run_dream_cycle
    from we_together.services.derivation_rebuild import get_insight_sources
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    pid = "p_df1"
    _seed_person(db, pid)
    for i in range(4):
        _seed_memory(db, f"m_src_{i}", pid, f"事件 {i}")

    r = run_dream_cycle(db, min_cluster_size=3,
                         archive_low_relevance=False)
    if not r["insights_created"]:
        import pytest
        pytest.skip("no insight created")

    info = get_insight_sources(db, r["insights_created"][0])
    assert info["is_insight"] is True
    assert info["rebuildable"] is True
    assert len(info["source_memory_ids"]) >= 3


def test_verify_insight_rebuildable(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.dream_cycle import run_dream_cycle
    from we_together.services.derivation_rebuild import verify_insight_rebuildable
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    pid = "p_df2"
    _seed_person(db, pid)
    for i in range(4):
        _seed_memory(db, f"m_vs_{i}", pid, f"x {i}")

    r = run_dream_cycle(db, min_cluster_size=3,
                         archive_low_relevance=False)
    if not r["insights_created"]:
        import pytest
        pytest.skip("no insight")
    assert verify_insight_rebuildable(db, r["insights_created"][0]) is True


def test_rebuild_activation_edge_stats(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record
    from we_together.services.derivation_rebuild import rebuild_activation_edge_stats
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    for _ in range(3):
        record(db, from_entity_type="person", from_entity_id="pA",
               to_entity_type="person", to_entity_id="pB",
               trace_type="scene_participation")
    record(db, from_entity_type="person", from_entity_id="pA",
           to_entity_type="person", to_entity_id="pC")

    stats = rebuild_activation_edge_stats(db, since_days=30)
    assert stats["total_edges"] >= 2
    top_edge = stats["top"][0]
    assert top_edge["count"] >= 1


def test_summary_healthy(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.derivation_rebuild import summary
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # 空图谱：no insights → healthy True
    s = summary(db)
    assert s["healthy"] is True
    assert s["insights_total"] == 0


def test_verify_narrative_arcs_rebuildable_missing(temp_project_with_migrations):
    """不存在的 arc → False"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.derivation_rebuild import verify_narrative_arcs_rebuildable
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    assert verify_narrative_arcs_rebuildable(db, "arc_does_not_exist") is False
