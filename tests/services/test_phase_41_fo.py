"""Phase 41 — 遗忘 / 压缩 / 拆分 (FO slices)。"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _seed_aged_memory(db: Path, mid: str, owner: str, relevance: float = 0.2,
                       days_ago: int = 60, status: str = "active") -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'shared_memory', ?, ?, 0.7, 1, ?, '{}',
               datetime('now', ?), datetime('now', ?))""",
            (mid, f"memory {mid}", relevance, status,
             f"-{days_ago} days", f"-{days_ago} days"),
        )
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, NULL)",
            (mid, owner),
        )
        conn.commit()
    finally:
        conn.close()


def test_forget_score_curve():
    from we_together.services.forgetting_service import _forget_score
    # 新近 + 高相关：接近 0
    assert _forget_score(days_idle=0, relevance=1.0) < 0.05
    # 久远 + 低相关：接近 1
    assert _forget_score(days_idle=365, relevance=0.0) > 0.8
    # 只有一个条件成立：中等
    mid = _forget_score(days_idle=60, relevance=0.3)
    assert 0.3 < mid < 0.8


def test_archive_stale_memories_dry_run(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.forgetting_service import (
        ForgetParams,
        archive_stale_memories,
    )

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_aged_memory(db, "m_old_1", "p1", relevance=0.2, days_ago=90)
    _seed_aged_memory(db, "m_old_2", "p1", relevance=0.3, days_ago=60)
    _seed_aged_memory(db, "m_new_1", "p1", relevance=0.9, days_ago=3)

    r = archive_stale_memories(db, ForgetParams(dry_run=True))
    assert r["dry_run"] is True
    assert r["archived_count"] >= 1

    # 确认 dry_run 没真 archive
    conn = sqlite3.connect(db)
    cnt = conn.execute(
        "SELECT COUNT(*) FROM memories WHERE status='cold'"
    ).fetchone()[0]
    conn.close()
    assert cnt == 0


def test_archive_stale_memories_real(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.forgetting_service import (
        ForgetParams,
        archive_stale_memories,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_aged_memory(db, "m_stale", "p2", relevance=0.1, days_ago=120)

    r = archive_stale_memories(db, ForgetParams(dry_run=False))
    assert r["archived_count"] >= 1

    conn = sqlite3.connect(db)
    s = conn.execute(
        "SELECT status FROM memories WHERE memory_id='m_stale'"
    ).fetchone()[0]
    conn.close()
    assert s == "cold"


def test_reactivate_memory_symmetric(temp_project_with_migrations):
    """不变式 #22: archive 可撤销"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.forgetting_service import (
        ForgetParams,
        archive_stale_memories,
        reactivate_memory,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_aged_memory(db, "m_revive", "p3", relevance=0.05, days_ago=200)
    archive_stale_memories(db, ForgetParams(dry_run=False))

    ok = reactivate_memory(db, "m_revive")
    assert ok is True

    conn = sqlite3.connect(db)
    s = conn.execute(
        "SELECT status FROM memories WHERE memory_id='m_revive'"
    ).fetchone()[0]
    conn.close()
    assert s == "active"


def test_condense_cluster_candidates(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.forgetting_service import condense_cluster_candidates
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # 同一 person 下 7 条 idle memory
    for i in range(7):
        _seed_aged_memory(db, f"m_cl_{i}", "person_hoarder", relevance=0.5, days_ago=70)
    r = condense_cluster_candidates(db, min_cluster_size=5, idle_days=60)
    assert len(r) == 1
    assert r[0]["person_id"] == "person_hoarder"
    assert r[0]["memory_count"] >= 7


def test_slimming_report(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.forgetting_service import slimming_report
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_aged_memory(db, "m_A", "p1", relevance=0.9, days_ago=1, status="active")
    _seed_aged_memory(db, "m_C", "p1", relevance=0.1, days_ago=200, status="cold")
    r = slimming_report(db)
    assert r["active"] >= 1
    assert r["cold"] >= 1
    assert 0.0 <= r["active_ratio"] <= 1.0


def test_unmerge_person_roundtrip(temp_project_with_migrations):
    """merge → unmerge 能成功，source 回 active"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.entity_unmerge_service import unmerge_person
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pS','source','merged',0.5,"
        "?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "pT"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pT','target','active',0.8,"
        "'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    r = unmerge_person(db, "pS", reviewer="test", reason="test-reverse")
    assert r["source_pid"] == "pS"
    assert r["target_pid"] == "pT"
    assert r["event_id"].startswith("evt_unmerge_")

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT status, metadata_json FROM persons WHERE person_id='pS'"
    ).fetchone()
    conn.close()
    assert row[0] == "active"
    meta = json.loads(row[1])
    assert "merged_into" not in meta
    assert "unmerge_history" in meta


def test_unmerge_rejects_non_merged(temp_project_with_migrations):
    import pytest

    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.entity_unmerge_service import unmerge_person
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pA','A','active',0.8,'{}',"
        "datetime('now'),datetime('now'))"
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="not in merged state"):
        unmerge_person(db, "pA")


def test_unmerge_rejects_missing_target(temp_project_with_migrations):
    import pytest

    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.entity_unmerge_service import unmerge_person
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_missing_target','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_target_gone"}),),
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="merged_into target not found"):
        unmerge_person(db, "p_missing_target")


def test_unmerge_rejects_non_active_target(temp_project_with_migrations):
    import pytest

    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.entity_unmerge_service import unmerge_person
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_inactive_target_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_inactive_target_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_inactive_target_tgt','tgt','inactive',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="merged_into target is not active"):
        unmerge_person(db, "p_inactive_target_src")


def test_list_merged_candidates(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.entity_unmerge_service import list_merged_candidates
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pS1','s1','merged',0.5, "
        "?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "pT1"}),),
    )
    conn.commit()
    conn.close()
    items = list_merged_candidates(db)
    assert len(items) == 1
    assert items[0]["source_pid"] == "pS1"


def test_derive_unmerge_from_contradictions_only_candidates(temp_project_with_migrations):
    """不变式 #18 + #22：contradiction → unmerge candidate 仅是 suggestion，不自动改图"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.entity_unmerge_service import (
        derive_unmerge_candidates_from_contradictions,
        list_merged_candidates,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pS2','s2','merged',0.5, "
        "?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "pT2"}),),
    )
    conn.commit()
    conn.close()

    before = len(list_merged_candidates(db))
    cands = derive_unmerge_candidates_from_contradictions(db)
    after = len(list_merged_candidates(db))

    # 函数调用不自动 unmerge
    assert before == after == 1
    assert len(cands) == 1
    assert "needs human gate" in cands[0]["note"]


def test_open_unmerge_branch_for_merged_person(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.entity_unmerge_service import list_merged_candidates
    from we_together.services.unmerge_gate_service import open_unmerge_branch_for_merged_person

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_gate_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_tgt','tgt','active',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    before = len(list_merged_candidates(db))
    result = open_unmerge_branch_for_merged_person(
        db,
        source_pid="p_gate_src",
        confidence=0.92,
        reason="contradiction-derived operator gate",
        note="memory mismatch",
    )
    after = len(list_merged_candidates(db))

    assert result["branch_id"].startswith("branch_unmerge_")
    assert result["source_pid"] == "p_gate_src"
    assert result["target_pid"] == "p_gate_tgt"
    assert before == after == 1

    conn = sqlite3.connect(db)
    branch = conn.execute(
        "SELECT status, reason FROM local_branches WHERE branch_id = ?",
        (result["branch_id"],),
    ).fetchone()
    cand_count = conn.execute(
        "SELECT COUNT(*) FROM branch_candidates WHERE branch_id = ?",
        (result["branch_id"],),
    ).fetchone()[0]
    conn.close()

    assert branch[0] == "open"
    assert "operator gate" in branch[1]
    assert cand_count == 2


def test_open_unmerge_branch_clamps_confidence_upper_bound(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.unmerge_gate_service import open_unmerge_branch_for_merged_person

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_high_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_gate_high_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_high_tgt','tgt','active',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    result = open_unmerge_branch_for_merged_person(
        db,
        source_pid="p_gate_high_src",
        confidence=1.7,
        reason="confidence should clamp high",
    )

    conn = sqlite3.connect(db)
    keep_conf = conn.execute(
        "SELECT confidence FROM branch_candidates WHERE candidate_id = ?",
        (result["keep_candidate_id"],),
    ).fetchone()[0]
    unmerge_conf = conn.execute(
        "SELECT confidence FROM branch_candidates WHERE candidate_id = ?",
        (result["unmerge_candidate_id"],),
    ).fetchone()[0]
    patch_conf = conn.execute(
        "SELECT confidence FROM patches WHERE target_id = ? AND operation = 'create_local_branch'",
        (result["branch_id"],),
    ).fetchone()[0]
    conn.close()

    assert keep_conf == 0.0
    assert unmerge_conf == 1.0
    assert patch_conf == 1.0


def test_open_unmerge_branch_clamps_confidence_lower_bound(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.unmerge_gate_service import open_unmerge_branch_for_merged_person

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_low_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_gate_low_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_low_tgt','tgt','active',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    result = open_unmerge_branch_for_merged_person(
        db,
        source_pid="p_gate_low_src",
        confidence=-0.3,
        reason="confidence should clamp low",
    )

    conn = sqlite3.connect(db)
    keep_conf = conn.execute(
        "SELECT confidence FROM branch_candidates WHERE candidate_id = ?",
        (result["keep_candidate_id"],),
    ).fetchone()[0]
    unmerge_conf = conn.execute(
        "SELECT confidence FROM branch_candidates WHERE candidate_id = ?",
        (result["unmerge_candidate_id"],),
    ).fetchone()[0]
    patch_conf = conn.execute(
        "SELECT confidence FROM patches WHERE target_id = ? AND operation = 'create_local_branch'",
        (result["branch_id"],),
    ).fetchone()[0]
    conn.close()

    assert keep_conf == 1.0
    assert unmerge_conf == 0.0
    assert patch_conf == 0.0


def test_open_unmerge_branch_rejects_missing_target(temp_project_with_migrations):
    import pytest

    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.unmerge_gate_service import open_unmerge_branch_for_merged_person

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_missing_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_gate_missing_tgt"}),),
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="merged_into target not found"):
        open_unmerge_branch_for_merged_person(
            db,
            source_pid="p_gate_missing_src",
            confidence=0.9,
            reason="contradiction-derived operator gate",
        )


def test_open_unmerge_branch_rejects_non_active_target(temp_project_with_migrations):
    import pytest

    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.unmerge_gate_service import open_unmerge_branch_for_merged_person

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_inactive_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_gate_inactive_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate_inactive_tgt','tgt','inactive',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="merged_into target is not active"):
        open_unmerge_branch_for_merged_person(
            db,
            source_pid="p_gate_inactive_src",
            confidence=0.9,
            reason="contradiction-derived operator gate",
        )


def test_operator_gate_branch_can_apply_unmerge_effect(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.patch_applier import apply_patch_record
    from we_together.services.patch_service import build_patch
    from we_together.services.unmerge_gate_service import open_unmerge_branch_for_merged_person

    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate2_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_gate2_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_gate2_tgt','tgt','active',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    proposal = open_unmerge_branch_for_merged_person(
        db,
        source_pid="p_gate2_src",
        confidence=0.88,
        reason="contradiction gate",
    )

    resolve_patch = build_patch(
        source_event_id="evt_gate_resolve",
        target_type="local_branch",
        target_id=proposal["branch_id"],
        operation="resolve_local_branch",
        payload={
            "branch_id": proposal["branch_id"],
            "status": "resolved",
            "reason": "operator approved unmerge",
            "selected_candidate_id": proposal["unmerge_candidate_id"],
        },
        confidence=1.0,
        reason="operator approved unmerge",
    )
    apply_patch_record(db_path=db, patch=resolve_patch)

    conn = sqlite3.connect(db)
    status = conn.execute(
        "SELECT status FROM persons WHERE person_id = 'p_gate2_src'"
    ).fetchone()[0]
    branch_status = conn.execute(
        "SELECT status FROM local_branches WHERE branch_id = ?",
        (proposal["branch_id"],),
    ).fetchone()[0]
    conn.close()

    assert status == "active"
    assert branch_status == "resolved"
