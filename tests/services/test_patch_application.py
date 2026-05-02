import json
import sqlite3

import pytest

from we_together.db.bootstrap import bootstrap_project
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


def test_apply_patch_record_can_create_memory(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    patch = build_patch(
        source_event_id="evt_1",
        target_type="memory",
        target_id="memory_1",
        operation="create_memory",
        payload={
            "memory_id": "memory_1",
            "memory_type": "shared_memory",
            "summary": "一起熬夜聊天",
            "confidence": 0.8,
            "is_shared": 1,
            "status": "active",
            "metadata_json": {"source_event_id": "evt_1"},
        },
        confidence=0.8,
        reason="test memory patch",
    )

    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT summary FROM memories WHERE memory_id = ?",
        ("memory_1",),
    ).fetchone()
    patch_row = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (patch["patch_id"],),
    ).fetchone()
    conn.close()

    assert row[0] == "一起熬夜聊天"
    assert patch_row[0] == "applied"


def test_apply_patch_record_can_update_state(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    patch = build_patch(
        source_event_id="evt_2",
        target_type="state",
        target_id="state_1",
        operation="update_state",
        payload={
            "state_id": "state_1",
            "scope_type": "scene",
            "scope_id": "scene_1",
            "state_type": "mood",
            "value_json": {"mood": "tense"},
            "confidence": 0.9,
            "is_inferred": 1,
            "decay_policy": None,
            "source_event_refs_json": ["evt_2"],
        },
        confidence=0.9,
        reason="test state patch",
    )

    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT value_json FROM states WHERE state_id = ?",
        ("state_1",),
    ).fetchone()
    conn.close()

    assert json.loads(row[0])["mood"] == "tense"


def test_apply_patch_record_can_link_entities(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    patch = build_patch(
        source_event_id="evt_3",
        target_type="entity_link",
        target_id=None,
        operation="link_entities",
        payload={
            "from_type": "memory",
            "from_id": "memory_a",
            "relation_type": "supports",
            "to_type": "memory",
            "to_id": "memory_b",
            "weight": 0.75,
            "metadata_json": {"context": "nightly session"},
        },
        confidence=0.6,
        reason="test entity link patch",
    )

    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT weight, metadata_json FROM entity_links WHERE from_type = ? AND from_id = ? AND to_id = ?",
        ("memory", "memory_a", "memory_b"),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] == 0.75
    assert json.loads(row[1])["context"] == "nightly session"


def test_apply_patch_record_can_create_local_branch(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    patch = build_patch(
        source_event_id="evt_4",
        target_type="local_branch",
        target_id="branch_1",
        operation="create_local_branch",
        payload={
            "branch_id": "branch_1",
            "scope_type": "relation",
            "scope_id": "relation_1",
            "status": "open",
            "reason": "conflicting relation evidence",
            "created_from_event_id": "evt_4",
            "branch_candidates": [
                {
                    "candidate_id": "candidate_a",
                    "label": "同事关系",
                    "payload_json": {"core_type": "work"},
                    "confidence": 0.7,
                    "status": "open",
                },
                {
                    "candidate_id": "candidate_b",
                    "label": "朋友关系",
                    "payload_json": {"core_type": "friendship"},
                    "confidence": 0.8,
                    "status": "open",
                },
            ],
        },
        confidence=0.7,
        reason="test local branch patch",
    )

    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT scope_type, scope_id, status, reason, created_from_event_id FROM local_branches WHERE branch_id = ?",
        ("branch_1",),
    ).fetchone()
    candidate_count = conn.execute(
        "SELECT COUNT(*) FROM branch_candidates WHERE branch_id = ?",
        ("branch_1",),
    ).fetchone()[0]
    branch_candidates = conn.execute(
        "SELECT candidate_id, label, payload_json, confidence, status FROM branch_candidates WHERE branch_id = ? ORDER BY candidate_id",
        ("branch_1",),
    ).fetchall()
    conn.close()

    assert row == ("relation", "relation_1", "open", "conflicting relation evidence", "evt_4")
    assert candidate_count == 2
    assert len(branch_candidates) == 2
    assert branch_candidates[0][0] == "candidate_a"
    assert branch_candidates[1][0] == "candidate_b"
    assert json.loads(branch_candidates[0][2])["core_type"] == "work"


def test_apply_patch_record_can_resolve_local_branch(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    create_patch = build_patch(
        source_event_id="evt_5",
        target_type="local_branch",
        target_id="branch_2",
        operation="create_local_branch",
        payload={
            "branch_id": "branch_2",
            "scope_type": "person",
            "scope_id": "person_1",
            "status": "open",
            "reason": "identity ambiguity",
            "created_from_event_id": "evt_5",
            "branch_candidates": [
                {
                    "candidate_id": "candidate_keep",
                    "label": "保留当前人设",
                    "payload_json": {"mode": "keep"},
                    "confidence": 0.5,
                    "status": "open",
                },
                {
                    "candidate_id": "candidate_merge",
                    "label": "合并身份",
                    "payload_json": {"mode": "merge"},
                    "confidence": 0.8,
                    "status": "open",
                },
            ],
        },
        confidence=0.6,
        reason="open local branch",
    )
    apply_patch_record(db_path=db_path, patch=create_patch)

    resolve_patch = build_patch(
        source_event_id="evt_6",
        target_type="local_branch",
        target_id="branch_2",
        operation="resolve_local_branch",
        payload={
            "branch_id": "branch_2",
            "status": "resolved",
            "resolved_at": "2026-04-09T12:00:00+08:00",
            "reason": "merged after confirmation",
            "selected_candidate_id": "candidate_merge",
        },
        confidence=0.8,
        reason="resolve local branch",
    )

    apply_patch_record(db_path=db_path, patch=resolve_patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT status, reason, resolved_at FROM local_branches WHERE branch_id = ?",
        ("branch_2",),
    ).fetchone()
    candidate_rows = conn.execute(
        "SELECT candidate_id, status FROM branch_candidates WHERE branch_id = ? ORDER BY candidate_id",
        ("branch_2",),
    ).fetchall()
    conn.close()

    assert row == ("resolved", "merged after confirmation", "2026-04-09T12:00:00+08:00")
    assert candidate_rows == [
        ("candidate_keep", "rejected"),
        ("candidate_merge", "selected"),
    ]


def test_apply_patch_record_marks_failed_for_unsupported_operation(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    patch = build_patch(
        source_event_id="evt_unsupported",
        target_type="unknown",
        target_id="unknown",
        operation="unsupported_operation",
        payload={},
        confidence=0.1,
        reason="unsupported"
    )

    with pytest.raises(ValueError):
        apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    patch_row = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (patch["patch_id"],),
    ).fetchone()
    conn.close()

    assert patch_row[0] == "failed"


def test_apply_patch_record_can_unlink_entities(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    link_patch = build_patch(
        source_event_id="evt_link",
        target_type="entity_link",
        target_id=None,
        operation="link_entities",
        payload={
            "from_type": "memory",
            "from_id": "memory_x",
            "relation_type": "supports",
            "to_type": "memory",
            "to_id": "memory_y",
            "weight": 0.6,
        },
        confidence=0.5,
        reason="link to remove",
    )

    apply_patch_record(db_path=db_path, patch=link_patch)

    unlink_patch = build_patch(
        source_event_id="evt_unlink",
        target_type="entity_link",
        target_id=None,
        operation="unlink_entities",
        payload={
            "from_type": "memory",
            "from_id": "memory_x",
            "relation_type": "supports",
            "to_type": "memory",
            "to_id": "memory_y",
        },
        confidence=0.4,
        reason="unlink to clean up",
    )

    apply_patch_record(db_path=db_path, patch=unlink_patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT 1 FROM entity_links WHERE from_type = ? AND from_id = ? AND to_id = ?",
        ("memory", "memory_x", "memory_y"),
    ).fetchone()
    patch_row = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (unlink_patch["patch_id"],),
    ).fetchone()
    conn.close()

    assert row is None
    assert patch_row[0] == "applied"


def test_apply_patch_record_can_mark_memory_inactive(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    create_patch = build_patch(
        source_event_id="evt_memory_create",
        target_type="memory",
        target_id="memory_z",
        operation="create_memory",
        payload={
            "memory_id": "memory_z",
            "memory_type": "shared_memory",
            "summary": "旧记忆",
            "confidence": 0.5,
            "is_shared": 1,
            "status": "active",
        },
        confidence=0.5,
        reason="seed memory",
    )
    apply_patch_record(db_path=db_path, patch=create_patch)

    inactive_patch = build_patch(
        source_event_id="evt_memory_inactive",
        target_type="memory",
        target_id="memory_z",
        operation="mark_inactive",
        payload={},
        confidence=0.4,
        reason="retire memory",
    )
    apply_patch_record(db_path=db_path, patch=inactive_patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT status FROM memories WHERE memory_id = ?",
        ("memory_z",),
    ).fetchone()
    patch_row = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (inactive_patch["patch_id"],),
    ).fetchone()
    conn.close()

    assert row[0] == "inactive"
    assert patch_row[0] == "applied"


def test_apply_patch_record_can_mark_relation_inactive(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO relations(
            relation_id, core_type, custom_label, summary, directionality,
            strength, stability, visibility, status, time_start, time_end,
            confidence, metadata_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            "relation_inactive_test",
            "friendship",
            "朋友",
            "旧关系",
            "bidirectional",
            0.5,
            0.5,
            "known",
            "active",
            None,
            None,
            0.6,
            "{}",
        ),
    )
    conn.commit()
    conn.close()

    inactive_patch = build_patch(
        source_event_id="evt_relation_inactive",
        target_type="relation",
        target_id="relation_inactive_test",
        operation="mark_inactive",
        payload={},
        confidence=0.4,
        reason="retire relation",
    )
    apply_patch_record(db_path=db_path, patch=inactive_patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT status FROM relations WHERE relation_id = ?",
        ("relation_inactive_test",),
    ).fetchone()
    conn.close()

    assert row[0] == "inactive"


def test_resolve_local_branch_applies_selected_candidate_effect(temp_project_with_migrations):
    """resolve 后被选中的 candidate 的 effect_patches 应用到图谱。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    create_patch = build_patch(
        source_event_id="evt_branch_effect",
        target_type="local_branch",
        target_id="branch_effect_1",
        operation="create_local_branch",
        payload={
            "branch_id": "branch_effect_1",
            "scope_type": "person",
            "scope_id": "person_effect",
            "status": "open",
            "reason": "test effect application",
            "created_from_event_id": "evt_branch_effect",
            "branch_candidates": [
                {
                    "candidate_id": "cand_effect_a",
                    "label": "应用状态 A",
                    "payload_json": {
                        "effect_patches": [
                            {
                                "target_type": "state",
                                "target_id": "state_effect_1",
                                "operation": "update_state",
                                "payload": {
                                    "state_id": "state_effect_1",
                                    "scope_type": "person",
                                    "scope_id": "person_effect",
                                    "state_type": "mood",
                                    "value_json": {"mood": "happy"},
                                },
                                "confidence": 0.9,
                                "reason": "effect from candidate",
                            }
                        ]
                    },
                    "confidence": 0.8,
                    "status": "open",
                },
                {
                    "candidate_id": "cand_effect_b",
                    "label": "不应用",
                    "payload_json": {"variant": "b"},
                    "confidence": 0.5,
                    "status": "open",
                },
            ],
        },
        confidence=0.7,
        reason="branch with effect",
    )
    apply_patch_record(db_path=db_path, patch=create_patch)

    resolve_patch = build_patch(
        source_event_id="evt_resolve_effect",
        target_type="local_branch",
        target_id="branch_effect_1",
        operation="resolve_local_branch",
        payload={
            "branch_id": "branch_effect_1",
            "status": "resolved",
            "reason": "selected candidate with effect",
            "selected_candidate_id": "cand_effect_a",
        },
        confidence=0.9,
        reason="resolve with effect",
    )
    apply_patch_record(db_path=db_path, patch=resolve_patch)

    conn = sqlite3.connect(db_path)
    state_row = conn.execute(
        "SELECT value_json FROM states WHERE state_id = ?",
        ("state_effect_1",),
    ).fetchone()
    conn.close()

    assert state_row is not None
    assert json.loads(state_row[0])["mood"] == "happy"


def test_resolve_local_branch_keeps_branch_open_when_effect_patch_fails(
    temp_project_with_migrations,
):
    """effect_patches 失败时，resolve_local_branch 不应先把 branch 标 resolved。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    create_patch = build_patch(
        source_event_id="evt_branch_effect_fail",
        target_type="local_branch",
        target_id="branch_effect_fail_1",
        operation="create_local_branch",
        payload={
            "branch_id": "branch_effect_fail_1",
            "scope_type": "person",
            "scope_id": "person_effect_fail",
            "status": "open",
            "reason": "test effect failure",
            "created_from_event_id": "evt_branch_effect_fail",
            "branch_candidates": [
                {
                    "candidate_id": "cand_effect_fail_a",
                    "label": "应用失败 effect",
                    "payload_json": {
                        "effect_patches": [
                            {
                                "target_type": "person",
                                "target_id": "p_effect_fail_src",
                                "operation": "unmerge_person",
                                "payload": {
                                    "source_person_id": "p_effect_fail_src",
                                    "reviewer": "effect_fail_test",
                                    "reason": "should fail because source is not merged",
                                },
                                "confidence": 0.9,
                                "reason": "effect from candidate should fail",
                            }
                        ]
                    },
                    "confidence": 0.8,
                    "status": "open",
                },
                {
                    "candidate_id": "cand_effect_fail_b",
                    "label": "不应用",
                    "payload_json": {"variant": "b"},
                    "confidence": 0.5,
                    "status": "open",
                },
            ],
        },
        confidence=0.7,
        reason="branch with failing effect",
    )
    apply_patch_record(db_path=db_path, patch=create_patch)

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_effect_fail_src','src','active',0.5,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    resolve_patch = build_patch(
        source_event_id="evt_resolve_effect_fail",
        target_type="local_branch",
        target_id="branch_effect_fail_1",
        operation="resolve_local_branch",
        payload={
            "branch_id": "branch_effect_fail_1",
            "status": "resolved",
            "reason": "selected candidate with failing effect",
            "selected_candidate_id": "cand_effect_fail_a",
        },
        confidence=0.9,
        reason="resolve with failing effect",
    )

    with pytest.raises(ValueError, match="not in merged state"):
        apply_patch_record(db_path=db_path, patch=resolve_patch)

    conn = sqlite3.connect(db_path)
    branch_row = conn.execute(
        "SELECT status FROM local_branches WHERE branch_id = ?",
        ("branch_effect_fail_1",),
    ).fetchone()
    candidate_rows = conn.execute(
        "SELECT candidate_id, status FROM branch_candidates WHERE branch_id = ? ORDER BY candidate_id",
        ("branch_effect_fail_1",),
    ).fetchall()
    parent_patch_row = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (resolve_patch["patch_id"],),
    ).fetchone()
    conn.close()

    assert branch_row[0] == "open"
    assert candidate_rows == [
        ("cand_effect_fail_a", "open"),
        ("cand_effect_fail_b", "open"),
    ]
    assert parent_patch_row[0] == "failed"


def test_resolve_local_branch_without_effect_payload_still_works(temp_project_with_migrations):
    """没有 effect_patches 的 candidate 解决后不报错。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    create_patch = build_patch(
        source_event_id="evt_branch_no_effect",
        target_type="local_branch",
        target_id="branch_no_effect_1",
        operation="create_local_branch",
        payload={
            "branch_id": "branch_no_effect_1",
            "scope_type": "person",
            "scope_id": "person_no_effect",
            "status": "open",
            "reason": "no effect test",
            "created_from_event_id": "evt_branch_no_effect",
            "branch_candidates": [
                {
                    "candidate_id": "cand_no_effect_a",
                    "label": "无 effect",
                    "payload_json": {"variant": "a"},
                    "confidence": 0.6,
                    "status": "open",
                },
            ],
        },
        confidence=0.5,
        reason="branch without effect",
    )
    apply_patch_record(db_path=db_path, patch=create_patch)

    resolve_patch = build_patch(
        source_event_id="evt_resolve_no_effect",
        target_type="local_branch",
        target_id="branch_no_effect_1",
        operation="resolve_local_branch",
        payload={
            "branch_id": "branch_no_effect_1",
            "status": "resolved",
            "reason": "resolved without effect",
            "selected_candidate_id": "cand_no_effect_a",
        },
        confidence=0.7,
        reason="resolve without effect",
    )
    apply_patch_record(db_path=db_path, patch=resolve_patch)

    conn = sqlite3.connect(db_path)
    branch_row = conn.execute(
        "SELECT status FROM local_branches WHERE branch_id = ?",
        ("branch_no_effect_1",),
    ).fetchone()
    candidate_row = conn.execute(
        "SELECT status FROM branch_candidates WHERE candidate_id = ?",
        ("cand_no_effect_a",),
    ).fetchone()
    conn.close()

    assert branch_row[0] == "resolved"
    assert candidate_row[0] == "selected"


def test_resolve_local_branch_rejects_candidate_outside_branch(
    temp_project_with_migrations,
):
    """selected_candidate_id 必须属于目标 branch。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    create_patch = build_patch(
        source_event_id="evt_invalid_branch_candidate_open",
        target_type="local_branch",
        target_id="branch_invalid_candidate",
        operation="create_local_branch",
        payload={
            "branch_id": "branch_invalid_candidate",
            "scope_type": "person",
            "scope_id": "person_invalid_candidate",
            "status": "open",
            "reason": "identity ambiguity",
            "created_from_event_id": "evt_invalid_branch_candidate_open",
            "branch_candidates": [
                {
                    "candidate_id": "cand_invalid_keep",
                    "label": "keep",
                    "payload_json": {"mode": "keep"},
                    "confidence": 0.4,
                    "status": "open",
                },
                {
                    "candidate_id": "cand_invalid_merge",
                    "label": "merge",
                    "payload_json": {"mode": "merge"},
                    "confidence": 0.9,
                    "status": "open",
                },
            ],
        },
        confidence=0.7,
        reason="open invalid candidate branch",
    )
    apply_patch_record(db_path=db_path, patch=create_patch)

    resolve_patch = build_patch(
        source_event_id="evt_invalid_branch_candidate_resolve",
        target_type="local_branch",
        target_id="branch_invalid_candidate",
        operation="resolve_local_branch",
        payload={
            "branch_id": "branch_invalid_candidate",
            "status": "resolved",
            "reason": "invalid candidate selection",
            "selected_candidate_id": "cand_not_in_branch",
        },
        confidence=0.9,
        reason="invalid candidate selection",
    )

    with pytest.raises(ValueError, match="selected candidate does not belong to branch"):
        apply_patch_record(db_path=db_path, patch=resolve_patch)

    conn = sqlite3.connect(db_path)
    branch_status = conn.execute(
        "SELECT status FROM local_branches WHERE branch_id = 'branch_invalid_candidate'"
    ).fetchone()[0]
    candidate_statuses = conn.execute(
        "SELECT status FROM branch_candidates WHERE branch_id = 'branch_invalid_candidate' ORDER BY candidate_id"
    ).fetchall()
    patch_status = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (resolve_patch["patch_id"],),
    ).fetchone()[0]
    conn.close()

    assert branch_status == "open"
    assert [row[0] for row in candidate_statuses] == ["open", "open"]
    assert patch_status == "failed"


def test_apply_patch_record_can_unmerge_person(temp_project_with_migrations):
    """unmerge_person patch 应调用 entity_unmerge_service，把 merged person 恢复 active。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_unmerge_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_unmerge_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_unmerge_tgt','tgt','active',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    patch = build_patch(
        source_event_id="evt_unmerge_patch",
        target_type="person",
        target_id="p_unmerge_src",
        operation="unmerge_person",
        payload={
            "source_person_id": "p_unmerge_src",
            "reviewer": "patch_test",
            "reason": "direct patch unmerge",
        },
        confidence=0.9,
        reason="direct patch unmerge",
    )
    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    status = conn.execute(
        "SELECT status FROM persons WHERE person_id = 'p_unmerge_src'"
    ).fetchone()[0]
    patch_status = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (patch["patch_id"],),
    ).fetchone()[0]
    conn.close()

    assert status == "active"
    assert patch_status == "applied"


def test_apply_patch_record_marks_unmerge_failed_when_service_raises(
    temp_project_with_migrations,
):
    """unmerge_person 失败时，patch 不应被误记为 applied。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_unmerge_bad','bad','active',0.5,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    patch = build_patch(
        source_event_id="evt_unmerge_patch_fail",
        target_type="person",
        target_id="p_unmerge_bad",
        operation="unmerge_person",
        payload={
            "source_person_id": "p_unmerge_bad",
            "reviewer": "patch_test",
            "reason": "direct patch unmerge should fail",
        },
        confidence=0.9,
        reason="direct patch unmerge should fail",
    )

    with pytest.raises(ValueError, match="not in merged state"):
        apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    patch_status = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (patch["patch_id"],),
    ).fetchone()[0]
    conn.close()

    assert patch_status == "failed"


def test_apply_patch_record_can_update_person_entity(temp_project_with_migrations):
    """update_entity 应能更新 person 的指定字段。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        ("person_update_test", "UpdateTest", "active", None, None, None, None, None, None, 0.5, "{}"),
    )
    conn.commit()
    conn.close()

    patch = build_patch(
        source_event_id="evt_update_entity",
        target_type="person",
        target_id="person_update_test",
        operation="update_entity",
        payload={
            "persona_summary": "外向热情",
            "style_summary": "说话直接",
            "confidence": 0.9,
        },
        confidence=0.8,
        reason="update person profile",
    )
    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT persona_summary, style_summary, confidence FROM persons WHERE person_id = ?",
        ("person_update_test",),
    ).fetchone()
    patch_row = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?",
        (patch["patch_id"],),
    ).fetchone()
    conn.close()

    assert row[0] == "外向热情"
    assert row[1] == "说话直接"
    assert row[2] == 0.9
    assert patch_row[0] == "applied"


def test_apply_patch_record_can_update_relation_entity(temp_project_with_migrations):
    """update_entity 应能更新 relation 的指定字段。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO relations(
            relation_id, core_type, custom_label, summary, directionality,
            strength, stability, visibility, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        ("relation_update_test", "friendship", "朋友", "老朋友", "bidirectional", 0.5, 0.5, "known", "active", 0.6, "{}"),
    )
    conn.commit()
    conn.close()

    patch = build_patch(
        source_event_id="evt_update_relation",
        target_type="relation",
        target_id="relation_update_test",
        operation="update_entity",
        payload={
            "strength": 0.9,
            "summary": "深厚的多年友谊",
        },
        confidence=0.85,
        reason="update relation strength",
    )
    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT strength, summary FROM relations WHERE relation_id = ?",
        ("relation_update_test",),
    ).fetchone()
    conn.close()

    assert row[0] == 0.9
    assert row[1] == "深厚的多年友谊"


def test_merge_entities_moves_identity_links(temp_project_with_migrations):
    """merge_entities 应将 identity_links 从 source person 迁移到 target person。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO persons(
            person_id, primary_name, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
        """,
        [("person_keep", "Alice"), ("person_remove", "Alice2")],
    )
    conn.executemany(
        """
        INSERT INTO identity_links(
            identity_id, person_id, platform, external_id, display_name, confidence,
            is_user_confirmed, is_active, metadata_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, 0.8, 0, 1, '{}', datetime('now'), datetime('now'))
        """,
        [
            ("id_keep", "person_keep", "email", "alice@a.com", "Alice"),
            ("id_remove", "person_remove", "wechat", "alice_wx", "Alice2"),
        ],
    )
    conn.commit()
    conn.close()

    patch = build_patch(
        source_event_id="evt_merge",
        target_type="person",
        target_id="person_keep",
        operation="merge_entities",
        payload={
            "source_person_id": "person_remove",
            "target_person_id": "person_keep",
        },
        confidence=0.9,
        reason="merge duplicate",
    )
    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    links = conn.execute(
        "SELECT person_id FROM identity_links ORDER BY platform",
    ).fetchall()
    source_status = conn.execute(
        "SELECT status, metadata_json FROM persons WHERE person_id = 'person_remove'",
    ).fetchone()
    patch_row = conn.execute(
        "SELECT status FROM patches WHERE patch_id = ?", (patch["patch_id"],),
    ).fetchone()
    conn.close()

    assert all(row[0] == "person_keep" for row in links)
    assert source_status[0] == "merged"
    assert json.loads(source_status[1]).get("merged_into") == "person_keep"
    assert patch_row[0] == "applied"


def test_merge_entities_migrates_memory_owners(temp_project_with_migrations):
    """merge_entities 应将 memory_owners 中 old person_id 迁移到 new person_id。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO persons(
            person_id, primary_name, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
        """,
        [("person_target", "Bob"), ("person_source", "Bob2")],
    )
    conn.execute(
        """
        INSERT INTO memories(
            memory_id, memory_type, summary, relevance_score, confidence,
            is_shared, status, metadata_json, created_at, updated_at
        ) VALUES('mem_mo', 'shared_memory', '共享记忆', 0.8, 0.7, 1, 'active', '{}', datetime('now'), datetime('now'))
        """,
    )
    conn.execute(
        """
        INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label)
        VALUES('mem_mo', 'person', 'person_source', NULL)
        """,
    )
    conn.commit()
    conn.close()

    patch = build_patch(
        source_event_id="evt_merge_mo",
        target_type="person",
        target_id="person_target",
        operation="merge_entities",
        payload={
            "source_person_id": "person_source",
            "target_person_id": "person_target",
        },
        confidence=0.9,
        reason="merge memory owners",
    )
    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    owner_row = conn.execute(
        "SELECT owner_id FROM memory_owners WHERE memory_id = 'mem_mo'",
    ).fetchone()
    conn.close()

    assert owner_row[0] == "person_target"
