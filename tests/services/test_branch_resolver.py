import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.branch_resolver_service import auto_resolve_branches
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.unmerge_gate_service import open_unmerge_branch_for_merged_person


def _open_branch(db_path, branch_id, candidates):
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id=f"evt_{branch_id}",
            target_type="local_branch",
            target_id=branch_id,
            operation="create_local_branch",
            payload={
                "branch_id": branch_id,
                "scope_type": "person",
                "scope_id": "person_x",
                "status": "open",
                "reason": "test",
                "branch_candidates": candidates,
            },
            confidence=0.6,
            reason="open branch",
        ),
    )


def test_auto_resolve_picks_dominant_candidate(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    _open_branch(db_path, "br_auto_1", [
        {"candidate_id": "c_win", "label": "merge", "payload_json": {},
         "confidence": 0.9, "status": "open"},
        {"candidate_id": "c_lose", "label": "new", "payload_json": {},
         "confidence": 0.3, "status": "open"},
    ])

    result = auto_resolve_branches(db_path, threshold=0.8, margin=0.2)
    assert result["resolved_count"] == 1

    conn = sqlite3.connect(db_path)
    br_status = conn.execute(
        "SELECT status FROM local_branches WHERE branch_id = 'br_auto_1'"
    ).fetchone()[0]
    winner_status = conn.execute(
        "SELECT status FROM branch_candidates WHERE candidate_id = 'c_win'"
    ).fetchone()[0]
    conn.close()
    assert br_status == "resolved"
    assert winner_status == "selected"


def test_auto_resolve_skips_close_call(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    _open_branch(db_path, "br_auto_2", [
        {"candidate_id": "c_a", "label": "a", "payload_json": {},
         "confidence": 0.6, "status": "open"},
        {"candidate_id": "c_b", "label": "b", "payload_json": {},
         "confidence": 0.55, "status": "open"},
    ])

    result = auto_resolve_branches(db_path, threshold=0.8, margin=0.2)
    assert result["resolved_count"] == 0

    conn = sqlite3.connect(db_path)
    br_status = conn.execute(
        "SELECT status FROM local_branches WHERE branch_id = 'br_auto_2'"
    ).fetchone()[0]
    conn.close()
    assert br_status == "open"


def test_auto_resolve_skips_below_threshold(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    _open_branch(db_path, "br_auto_3", [
        {"candidate_id": "c_low", "label": "x", "payload_json": {},
         "confidence": 0.5, "status": "open"},
    ])

    result = auto_resolve_branches(db_path, threshold=0.8, margin=0.1)
    assert result["resolved_count"] == 0


def test_auto_resolve_skips_operator_gated_unmerge_branch(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_auto_gate_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        ('{"merged_into":"p_auto_gate_tgt"}',),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_auto_gate_tgt','tgt','active',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    proposal = open_unmerge_branch_for_merged_person(
        db_path,
        source_pid="p_auto_gate_src",
        confidence=0.92,
        reason="contradiction-derived operator gate",
    )

    result = auto_resolve_branches(db_path, threshold=0.8, margin=0.2)
    assert result["resolved_count"] == 0

    conn = sqlite3.connect(db_path)
    branch_status = conn.execute(
        "SELECT status FROM local_branches WHERE branch_id = ?",
        (proposal["branch_id"],),
    ).fetchone()[0]
    person_status = conn.execute(
        "SELECT status FROM persons WHERE person_id = 'p_auto_gate_src'"
    ).fetchone()[0]
    conn.close()

    assert branch_status == "open"
    assert person_status == "merged"
