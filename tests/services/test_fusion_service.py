import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.candidate_store import (
    write_identity_candidate,
    write_relation_clue,
)
from we_together.services.fusion_service import (
    fuse_identity_candidates,
    fuse_relation_clues,
    fuse_all,
)


def _seed_evidence(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO import_jobs(import_job_id, source_type, status, started_at)
        VALUES('job_fuse', 'manual', 'completed', datetime('now'))
        """
    )
    conn.execute(
        """
        INSERT INTO raw_evidences(
            evidence_id, import_job_id, source_type, content_type,
            normalized_text, created_at
        ) VALUES('evd_fuse', 'job_fuse', 'manual', 'text', 'sample', datetime('now'))
        """
    )
    conn.commit()
    conn.close()


def _seed_event(db_path, event_id="evt_fuse"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO events(
            event_id, event_type, source_type, timestamp, summary, visibility_level,
            confidence, is_structured, raw_evidence_refs_json, metadata_json, created_at
        ) VALUES(?, 'narration_seed', 'manual', datetime('now'), 'fuse test',
                 'visible', 0.8, 0, '[]', '{}', datetime('now'))
        """,
        (event_id,),
    )
    conn.commit()
    conn.close()


def test_fuse_identity_candidates_creates_new_person(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    cid = write_identity_candidate(
        db_path=db_path,
        evidence_id="evd_fuse",
        platform="email",
        external_id="alice@a.com",
        display_name="Alice",
        confidence=0.9,
    )

    result = fuse_identity_candidates(db_path)
    assert result["fused_count"] == 1
    assert result["created_persons"] == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT linked_person_id FROM identity_candidates WHERE candidate_id = ?", (cid,),
    ).fetchone()
    conn.close()
    assert row[0] is not None


def test_fuse_identity_candidates_reuses_same_name(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    write_identity_candidate(
        db_path=db_path,
        evidence_id="evd_fuse",
        platform="email",
        external_id="alice@a.com",
        display_name="Alice",
        confidence=0.9,
    )
    write_identity_candidate(
        db_path=db_path,
        evidence_id="evd_fuse",
        platform="wechat",
        external_id="alice_wx",
        display_name="Alice",
        confidence=0.8,
    )

    result = fuse_identity_candidates(db_path)
    assert result["fused_count"] == 2
    assert result["created_persons"] == 1
    assert result["reused_persons"] == 1

    conn = sqlite3.connect(db_path)
    persons = conn.execute(
        "SELECT person_id FROM persons WHERE primary_name = 'Alice'",
    ).fetchall()
    identity_count = conn.execute(
        "SELECT COUNT(*) FROM identity_links WHERE person_id = ?", (persons[0][0],),
    ).fetchone()[0]
    conn.close()

    assert len(persons) == 1
    assert identity_count == 2


def test_fuse_relation_clue_creates_relation(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)
    _seed_event(db_path)

    cid_a = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="Bob", confidence=0.9,
    )
    cid_b = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="Carol", confidence=0.9,
    )
    fuse_identity_candidates(db_path)

    write_relation_clue(
        db_path=db_path,
        evidence_id="evd_fuse",
        participant_candidate_ids=[cid_a, cid_b],
        core_type_hint="friendship",
        strength_hint=0.7,
        confidence=0.8,
    )

    result = fuse_relation_clues(db_path, source_event_id="evt_fuse")
    assert result["fused_count"] == 1
    assert result["created_relations"] == 1

    conn = sqlite3.connect(db_path)
    rel_count = conn.execute(
        "SELECT COUNT(*) FROM relations WHERE core_type = 'friendship'",
    ).fetchone()[0]
    et = conn.execute(
        "SELECT COUNT(*) FROM event_targets WHERE event_id = ? AND target_type = 'relation'",
        ("evt_fuse",),
    ).fetchone()[0]
    conn.close()

    assert rel_count == 1
    assert et == 1


def test_fuse_relation_clue_skips_when_participants_unlinked(temp_project_with_migrations):
    """未经 identity fusion 的 candidate 应被跳过。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    cid_a = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="Dan", confidence=0.5,
    )
    cid_b = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="Eve", confidence=0.5,
    )
    write_relation_clue(
        db_path=db_path,
        evidence_id="evd_fuse",
        participant_candidate_ids=[cid_a, cid_b],
        core_type_hint="friendship",
        confidence=0.7,
    )

    result = fuse_relation_clues(db_path)
    assert result["fused_count"] == 0
    assert result["skipped"] == 1


def test_fuse_all_runs_both(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)
    _seed_event(db_path)

    cid_a = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="Frank", confidence=0.8,
    )
    cid_b = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="Grace", confidence=0.8,
    )
    write_relation_clue(
        db_path=db_path,
        evidence_id="evd_fuse",
        participant_candidate_ids=[cid_a, cid_b],
        core_type_hint="colleague",
        confidence=0.7,
    )

    out = fuse_all(db_path, source_event_id="evt_fuse")
    assert out["identity"]["fused_count"] == 2
    assert out["relation"]["fused_count"] == 1


def test_low_tier_name_collision_opens_local_branch(temp_project_with_migrations):
    """low-tier 且同名 → 开 branch，而非直接合并。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)
    _seed_event(db_path)

    # 高置信先落：Harvey
    write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse",
        platform="email", external_id="h1@a.com",
        display_name="Harvey", confidence=0.9,
    )
    fuse_identity_candidates(db_path)

    # 低置信第二条：同名但 external_id 不同
    write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse",
        platform="wechat", external_id="harvey_wx",
        display_name="Harvey", confidence=0.2,  # low tier
    )
    result = fuse_identity_candidates(db_path, source_event_id="evt_fuse")

    assert result["branched"] == 1
    assert result["fused_count"] == 0

    conn = sqlite3.connect(db_path)
    branches = conn.execute(
        "SELECT branch_id, status FROM local_branches WHERE scope_type = 'person'",
    ).fetchall()
    branch_candidates = conn.execute(
        "SELECT COUNT(*) FROM branch_candidates",
    ).fetchone()[0]
    conn.close()

    assert len(branches) == 1
    assert branches[0][1] == "open"
    assert branch_candidates == 2  # merge + new


def test_low_tier_without_conflict_does_not_branch(temp_project_with_migrations):
    """low-tier 但无同名 → 正常新建 person，不开 branch。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="Ivy", confidence=0.2,
    )
    result = fuse_identity_candidates(db_path)

    assert result["branched"] == 0
    assert result["created_persons"] == 1


def test_fuse_group_clue_creates_group_and_members(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_evidence(db_path)

    cid_a = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="GA", confidence=0.9,
    )
    cid_b = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="GB", confidence=0.9,
    )
    cid_c = write_identity_candidate(
        db_path=db_path, evidence_id="evd_fuse", display_name="GC", confidence=0.9,
    )
    fuse_identity_candidates(db_path)

    from we_together.services.candidate_store import write_group_clue
    write_group_clue(
        db_path=db_path, evidence_id="evd_fuse",
        group_type_hint="team", group_name_hint="Mock Team",
        member_candidate_ids=[cid_a, cid_b, cid_c],
        confidence=0.8,
    )

    from we_together.services.fusion_service import fuse_group_clues
    out = fuse_group_clues(db_path)
    assert out["fused_count"] == 1
    assert out["created_groups"] == 1

    conn = sqlite3.connect(db_path)
    member_count = conn.execute(
        "SELECT COUNT(*) FROM group_members WHERE group_id IN (SELECT group_id FROM groups WHERE name = 'Mock Team')"
    ).fetchone()[0]
    conn.close()
    assert member_count == 3
