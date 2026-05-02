import json
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.candidate_store import (
    write_identity_candidate,
    write_event_candidate,
    write_facet_candidate,
    write_relation_clue,
    write_group_clue,
    list_open_candidates,
    mark_candidate_linked,
    _tier_from_score,
)


def _seed_evidence(db_path, evidence_id="evd_test"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO import_jobs(import_job_id, source_type, status, started_at)
        VALUES('job_test', 'manual', 'completed', datetime('now'))
        """
    )
    conn.execute(
        """
        INSERT INTO raw_evidences(
            evidence_id, import_job_id, source_type, content_type,
            normalized_text, created_at
        ) VALUES(?, 'job_test', 'manual', 'text', 'sample', datetime('now'))
        """,
        (evidence_id,),
    )
    conn.commit()
    conn.close()


def test_tier_from_score():
    assert _tier_from_score(0.9) == "high"
    assert _tier_from_score(0.5) == "medium"
    assert _tier_from_score(0.2) == "low"


def test_write_identity_candidate_persists_row(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    cid = write_identity_candidate(
        db_path=db_path,
        evidence_id="evd_test",
        platform="email",
        external_id="a@a.com",
        display_name="Alice",
        aliases=["A"],
        contact={"email": "a@a.com"},
        confidence=0.85,
    )

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT platform, external_id, display_name, aliases_json, confidence_tier, status FROM identity_candidates WHERE candidate_id = ?",
        (cid,),
    ).fetchone()
    conn.close()

    assert row[0] == "email"
    assert row[1] == "a@a.com"
    assert row[2] == "Alice"
    assert json.loads(row[3]) == ["A"]
    assert row[4] == "high"
    assert row[5] == "open"


def test_write_event_candidate_persists(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    cid = write_event_candidate(
        db_path=db_path,
        evidence_id="evd_test",
        event_type="dialogue",
        actor_candidate_ids=["idc_a"],
        summary="chatted",
        confidence=0.6,
    )
    rows = list_open_candidates(db_path, "event_candidates")
    assert any(r["candidate_id"] == cid for r in rows)
    assert rows[0]["confidence_tier"] == "medium"


def test_write_facet_candidate(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    cid = write_facet_candidate(
        db_path=db_path,
        evidence_id="evd_test",
        facet_type="work",
        facet_key="role",
        facet_value="engineer",
        target_person_id="person_x",
        confidence=0.8,
    )
    rows = list_open_candidates(db_path, "facet_candidates")
    assert len(rows) == 1
    assert rows[0]["facet_type"] == "work"


def test_write_relation_clue_and_group_clue(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    write_relation_clue(
        db_path=db_path,
        evidence_id="evd_test",
        participant_candidate_ids=["idc_a", "idc_b"],
        core_type_hint="friendship",
        strength_hint=0.7,
        confidence=0.7,
    )
    write_group_clue(
        db_path=db_path,
        evidence_id="evd_test",
        group_type_hint="team",
        group_name_hint="核心组",
        member_candidate_ids=["idc_a", "idc_b"],
        confidence=0.6,
    )
    assert len(list_open_candidates(db_path, "relation_clues")) == 1
    assert len(list_open_candidates(db_path, "group_clues")) == 1


def test_mark_candidate_linked_updates_status(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    cid = write_identity_candidate(
        db_path=db_path,
        evidence_id="evd_test",
        display_name="Bob",
        confidence=0.5,
    )
    mark_candidate_linked(
        db_path,
        "identity_candidates",
        "candidate_id",
        cid,
        link_col="linked_person_id",
        link_id="person_bob",
    )

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT status, linked_person_id FROM identity_candidates WHERE candidate_id = ?",
        (cid,),
    ).fetchone()
    conn.close()
    assert row[0] == "linked"
    assert row[1] == "person_bob"
