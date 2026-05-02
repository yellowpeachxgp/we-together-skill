from we_together.db.bootstrap import bootstrap_project
from we_together.runtime.sqlite_retrieval import build_runtime_retrieval_package_from_db
from we_together.services.group_service import create_group, add_group_member
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.scene_service import create_scene, add_scene_participant, close_scene
from we_together.services.ingestion_service import ingest_narration, ingest_text_chat
import sqlite3
import pytest


def test_build_runtime_retrieval_package_from_db_reads_scene_and_participants(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="late night remote chat",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
            "time_scope": "late_night",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=0.95,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)

    assert package["scene_summary"]["scene_id"] == scene_id
    assert package["environment_constraints"]["channel_scope"] == "private_dm"
    assert len(package["participants"]) == 1
    assert package["activation_map"][0]["activation_state"] == "explicit"


def test_retrieval_package_can_roundtrip_through_cache(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="cached scene",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_cache",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    first_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_1",
    )

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        UPDATE scene_participants
        SET activation_state = 'latent', activation_score = 0.1, is_speaking = 0
        WHERE scene_id = ? AND person_id = ?
        """,
        (scene_id, "person_cache"),
    )
    conn.commit()
    cache_rows = conn.execute(
        "SELECT COUNT(*) FROM retrieval_cache WHERE scene_id = ? AND input_hash = ?",
        (scene_id, "hash_1"),
    ).fetchone()[0]
    conn.close()

    second_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_1",
    )

    assert cache_rows == 1
    assert first_package["activation_map"][0]["activation_state"] == "explicit"
    assert second_package["activation_map"][0]["activation_state"] == "explicit"


def test_retrieval_cache_ttl_allows_refresh(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="ttl cache scene",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_ttl_one",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    first_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="ttl_refresh",
        cache_ttl_seconds=0,
    )

    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_ttl_two",
        activation_state="latent",
        activation_score=0.5,
        is_speaking=False,
    )

    second_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="ttl_refresh",
        cache_ttl_seconds=0,
    )

    assert len(first_package["participants"]) == 1
    assert len(second_package["participants"]) == 2

def test_scene_mutation_invalidates_retrieval_cache(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="cache invalidation scene",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_cache_a",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    first_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_scene_mutation",
    )

    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_cache_b",
        activation_state="latent",
        activation_score=0.5,
        is_speaking=False,
    )

    second_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_scene_mutation",
    )

    assert len(first_package["participants"]) == 1
    assert len(second_package["participants"]) == 2


def test_patch_application_invalidates_retrieval_cache(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="cache invalidation patch",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_cache_patch",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    first_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_patch_mutation",
    )

    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_patch_cache",
            target_type="state",
            target_id="state_cache_patch",
            operation="update_state",
            payload={
                "state_id": "state_cache_patch",
                "scope_type": "scene",
                "scope_id": scene_id,
                "state_type": "mood",
                "value_json": {"mood": "tense"},
            },
            confidence=0.8,
            reason="cache invalidation state patch",
        ),
    )

    second_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_patch_mutation",
    )

    assert first_package["current_states"] == []
    assert len(second_package["current_states"]) == 1


def test_group_mutation_invalidates_retrieval_cache(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    group_id = create_group(
        db_path=db_path,
        group_type="team",
        name="缓存小组",
        summary="cache group",
    )
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_a", role_label="owner")

    scene_id = create_scene(
        db_path=db_path,
        scene_type="work_discussion",
        scene_summary="group cache invalidation",
        environment={
            "location_scope": "remote",
            "channel_scope": "group_channel",
            "visibility_scope": "group_visible",
        },
        group_id=group_id,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_a",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    first_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_group_mutation",
    )

    add_group_member(db_path=db_path, group_id=group_id, person_id="person_b", role_label="member")

    second_package = build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_group_mutation",
    )

    assert first_package["safety_and_budget"]["source_counts"]["group"]["used"] == 0
    assert second_package["safety_and_budget"]["source_counts"]["group"]["used"] >= 1


def test_build_runtime_retrieval_package_uses_person_names_and_active_relations(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    people = {
        row[1]: row[0]
        for row in conn.execute("SELECT person_id, primary_name FROM persons").fetchall()
    }
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="friends chat",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小王"],
        activation_state="explicit",
        activation_score=0.95,
        is_speaking=True,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小李"],
        activation_state="latent",
        activation_score=0.85,
        is_speaking=False,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    conn = sqlite3.connect(db_path)
    persisted_relation_ids = {
        row[0]
        for row in conn.execute(
            "SELECT relation_id FROM scene_active_relations WHERE scene_id = ?",
            (scene_id,),
        ).fetchall()
    }
    conn.close()

    display_names = {item["display_name"] for item in package["participants"]}
    assert "小王" in display_names
    assert "小李" in display_names
    assert len(package["active_relations"]) >= 1
    assert len(package["relevant_memories"]) >= 1
    assert {
        item["relation_id"] for item in package["active_relations"]
    } == persisted_relation_ids


def test_retrieval_package_includes_group_context_when_scene_has_group(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    group_id = create_group(
        db_path=db_path,
        group_type="team",
        name="核心团队",
        summary="主开发小组",
    )
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_alice", role_label="owner")

    scene_id = create_scene(
        db_path=db_path,
        scene_type="work_discussion",
        scene_summary="team sync",
        environment={
            "location_scope": "remote",
            "channel_scope": "group_channel",
            "visibility_scope": "group_visible",
        },
        group_id=group_id,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)

    assert package["scene_summary"]["group_id"] == group_id
    assert package["group_context"]["group_id"] == group_id
    assert package["group_context"]["name"] == "核心团队"


def test_retrieval_package_includes_state_scopes_and_relation_participants(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    people = {
        row[1]: row[0]
        for row in conn.execute("SELECT person_id, primary_name FROM persons").fetchall()
    }
    relation_id = conn.execute("SELECT relation_id FROM relations LIMIT 1").fetchone()[0]
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="friends chat",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小王"],
        activation_state="explicit",
        activation_score=0.95,
        is_speaking=True,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小李"],
        activation_state="latent",
        activation_score=0.85,
        is_speaking=False,
    )

    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_scene_state",
            target_type="state",
            target_id="state_scene_1",
            operation="update_state",
            payload={
                "state_id": "state_scene_1",
                "scope_type": "scene",
                "scope_id": scene_id,
                "state_type": "mood",
                "value_json": {"mood": "warm"},
            },
            confidence=0.8,
            reason="scene state",
        ),
    )
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_person_state",
            target_type="state",
            target_id="state_person_1",
            operation="update_state",
            payload={
                "state_id": "state_person_1",
                "scope_type": "person",
                "scope_id": people["小王"],
                "state_type": "energy",
                "value_json": {"energy": "tired"},
            },
            confidence=0.7,
            reason="person state",
        ),
    )
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_relation_state",
            target_type="state",
            target_id="state_relation_1",
            operation="update_state",
            payload={
                "state_id": "state_relation_1",
                "scope_type": "relation",
                "scope_id": relation_id,
                "state_type": "tone",
                "value_json": {"tone": "trusting"},
            },
            confidence=0.75,
            reason="relation state",
        ),
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)

    relation_entry = package["active_relations"][0]
    relation_participants = {item["display_name"] for item in relation_entry["participants"]}
    state_scopes = {(item["scope_type"], item["scope_id"]) for item in package["current_states"]}

    assert relation_participants == {"小王", "小李"}
    assert ("scene", scene_id) in state_scopes
    assert ("person", people["小王"]) in state_scopes
    assert ("relation", relation_id) in state_scopes


def test_inferred_text_chat_state_flows_into_current_states(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    from we_together.services.ingestion_service import ingest_text_chat

    ingest_text_chat(
        db_path=db_path,
        transcript="2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n",
        source_name="chat.txt",
    )

    conn = sqlite3.connect(db_path)
    people = {
        row[1]: row[0]
        for row in conn.execute("SELECT person_id, primary_name FROM persons").fetchall()
    }
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="state retrieval",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小王"],
        activation_state="explicit",
        activation_score=0.95,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    person_states = [
        item for item in package["current_states"]
        if item["scope_type"] == "person" and item["scope_id"] == people["小王"]
    ]

    assert any(item["state_type"] == "energy" for item in person_states)


def test_retrieval_package_ignores_inactive_relation_and_memory(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    people = {
        row[1]: row[0]
        for row in conn.execute("SELECT person_id, primary_name FROM persons").fetchall()
    }
    relation_id = conn.execute("SELECT relation_id FROM relations LIMIT 1").fetchone()[0]
    memory_id = conn.execute("SELECT memory_id FROM memories LIMIT 1").fetchone()[0]
    conn.close()

    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_relation_inactive",
            target_type="relation",
            target_id=relation_id,
            operation="mark_inactive",
            payload={},
            confidence=0.5,
            reason="retire relation",
        ),
    )
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_memory_inactive",
            target_type="memory",
            target_id=memory_id,
            operation="mark_inactive",
            payload={},
            confidence=0.5,
            reason="retire memory",
        ),
    )

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="inactive filter test",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小王"],
        activation_state="explicit",
        activation_score=0.9,
        is_speaking=True,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小李"],
        activation_state="latent",
        activation_score=0.8,
        is_speaking=False,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)

    relation_ids = {item["relation_id"] for item in package["active_relations"]}
    memory_ids = {item["memory_id"] for item in package["relevant_memories"]}

    assert relation_id not in relation_ids
    assert memory_id not in memory_ids


def test_runtime_retrieval_ignores_directly_inactive_relations(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    person_primary = "person_runtime_rel_primary"
    person_other = "person_runtime_rel_other"
    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        [
            (
                person_primary,
                "PrimaryRel",
                "active",
                None,
                None,
                None,
                None,
                None,
                None,
                0.85,
                "{}",
            ),
            (
                person_other,
                "OtherRel",
                "active",
                None,
                None,
                None,
                None,
                None,
                None,
                0.85,
                "{}",
            ),
        ],
    )

    inactive_relation_id = "relation_runtime_inactive"
    conn.execute(
        """
        INSERT INTO relations(
            relation_id, core_type, custom_label, summary, directionality,
            strength, stability, visibility, status, time_start, time_end,
            confidence, metadata_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            inactive_relation_id,
            "colleague",
            "Inactive relation",
            "Should be dropped from retrieval",
            "bidirectional",
            0.5,
            0.4,
            "known",
            "inactive",
            None,
            None,
            0.7,
            "{}",
        ),
    )
    event_id = "evt_runtime_inactive_relation"
    conn.execute(
        """
        INSERT INTO events(
            event_id, event_type, source_type, scene_id, group_id,
            timestamp, summary, visibility_level, confidence, is_structured,
            raw_evidence_refs_json, metadata_json, created_at
        ) VALUES(?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            event_id,
            "narration_seed",
            "manual",
            None,
            None,
            "trigger relation retrieval",
            "visible",
            0.9,
            0,
            "[]",
            "{}",
        ),
    )
    conn.executemany(
        """
        INSERT INTO event_participants(event_id, person_id, participant_role)
        VALUES(?, ?, ?)
        """,
        [
            (event_id, person_primary, "speaker"),
            (event_id, person_other, "mentioned"),
        ],
    )
    conn.execute(
        """
        INSERT INTO event_targets(event_id, target_type, target_id, impact_hint)
        VALUES(?, ?, ?, ?)
        """,
        (event_id, "relation", inactive_relation_id, "inactive test"),
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="inactive relation filtering",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=person_primary,
        activation_state="explicit",
        activation_score=0.95,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    relation_ids = {item["relation_id"] for item in package["active_relations"]}

    assert inactive_relation_id not in relation_ids


def test_runtime_retrieval_ignores_directly_inactive_memories(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    person_id = "person_runtime_memory"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            person_id,
            "MemoryTester",
            "active",
            None,
            None,
            None,
            None,
            None,
            None,
            0.8,
            "{}",
        ),
    )

    active_memory_id = "memory_runtime_active"
    inactive_memory_id = "memory_runtime_inactive"
    conn.executemany(
        """
        INSERT INTO memories(
            memory_id, memory_type, summary, emotional_tone, relevance_score,
            confidence, is_shared, status, metadata_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        [
            (
                active_memory_id,
                "shared_memory",
                "Active runtime memory",
                None,
                0.9,
                0.85,
                1,
                "active",
                "{}",
            ),
            (
                inactive_memory_id,
                "shared_memory",
                "Inactive runtime memory",
                None,
                0.8,
                0.75,
                1,
                "inactive",
                "{}",
            ),
        ],
    )
    conn.executemany(
        """
        INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label)
        VALUES(?, ?, ?, ?)
        """,
        [
            (active_memory_id, "person", person_id, None),
            (inactive_memory_id, "person", person_id, None),
        ],
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="inactive memory filtering",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=person_id,
        activation_state="explicit",
        activation_score=0.95,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    memory_ids = {item["memory_id"] for item in package["relevant_memories"]}

    assert active_memory_id in memory_ids
    assert inactive_memory_id not in memory_ids


def test_group_scene_adds_group_members_as_latent_activation(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    group_id = create_group(
        db_path=db_path,
        group_type="team",
        name="核心团队",
        summary="主开发小组",
    )
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_alice", role_label="owner")
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_bob", role_label="member")

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        ("person_alice", "Alice", "active", None, None, None, None, None, None, 0.8, "{}"),
    )
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        ("person_bob", "Bob", "active", None, None, None, None, None, None, 0.8, "{}"),
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="work_discussion",
        scene_summary="team sync",
        environment={
            "location_scope": "remote",
            "channel_scope": "group_channel",
            "visibility_scope": "group_visible",
        },
        group_id=group_id,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)

    activation_map = {item["person_id"]: item for item in package["activation_map"]}

    assert activation_map["person_bob"]["activation_state"] == "latent"
    assert activation_map["person_bob"]["activation_score"] > 0
    assert package["response_policy"]["mode"] == "primary_plus_support"


def test_shared_memory_can_activate_latent_participant_without_group_context(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    people = {
        row[1]: row[0]
        for row in conn.execute("SELECT person_id, primary_name FROM persons").fetchall()
    }
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="memory recall",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小王"],
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    activation_map = {item["person_id"]: item for item in package["activation_map"]}

    assert activation_map[people["小李"]]["activation_state"] == "latent"
    assert activation_map[people["小李"]]["activation_score"] > 0
    assert package["response_policy"]["mode"] == "single_primary"
    assert package["response_policy"]["primary_speaker"] == people["小王"]


def test_active_relation_can_activate_latent_participant_without_group_context(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now')),
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            "person_alice", "Alice", "active", None, None, None, None, None, None, 0.8, "{}",
            "person_carla", "Carla", "active", None, None, None, None, None, None, 0.8, "{}",
        ),
    )
    conn.execute(
        """
        INSERT INTO relations(
            relation_id, core_type, custom_label, summary, directionality,
            strength, stability, visibility, status, time_start, time_end,
            confidence, metadata_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            "relation_ac",
            "friendship",
            "朋友",
            "Alice 与 Carla 关系亲近",
            "bidirectional",
            0.7,
            0.6,
            "known",
            "active",
            None,
            None,
            0.7,
            "{}",
        ),
    )
    conn.execute(
        """
        INSERT INTO events(
            event_id, event_type, source_type, scene_id, group_id,
            timestamp, summary, visibility_level, confidence, is_structured,
            raw_evidence_refs_json, metadata_json, created_at
        ) VALUES(?, ?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            "evt_relation_seed",
            "narration_imported",
            "manual",
            None,
            None,
            "Alice remembers Carla",
            "visible",
            0.8,
            0,
            "[]",
            "{}",
        ),
    )
    conn.executemany(
        """
        INSERT INTO event_participants(event_id, person_id, participant_role)
        VALUES(?, ?, ?)
        """,
        [
            ("evt_relation_seed", "person_alice", "mentioned"),
            ("evt_relation_seed", "person_carla", "mentioned"),
        ],
    )
    conn.execute(
        """
        INSERT INTO event_targets(event_id, target_type, target_id, impact_hint)
        VALUES(?, ?, ?, ?)
        """,
        ("evt_relation_seed", "relation", "relation_ac", "朋友"),
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="alice solo chat",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    activation_map = {item["person_id"]: item for item in package["activation_map"]}

    assert activation_map["person_carla"]["activation_state"] == "latent"
    assert activation_map["person_carla"]["activation_score"] > 0
    assert package["response_policy"]["mode"] == "single_primary"


def test_strict_activation_barrier_blocks_derived_latent_activation(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    group_id = create_group(
        db_path=db_path,
        group_type="team",
        name="核心团队",
        summary="主开发小组",
    )
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_alice", role_label="owner")
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_bob", role_label="member")

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now')),
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            "person_alice", "Alice", "active", None, None, None, None, None, None, 0.8, "{}",
            "person_bob", "Bob", "active", None, None, None, None, None, None, 0.8, "{}",
        ),
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="work_discussion",
        scene_summary="strict team sync",
        environment={
            "location_scope": "remote",
            "channel_scope": "group_channel",
            "visibility_scope": "group_visible",
            "activation_barrier": "strict",
        },
        group_id=group_id,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    activation_map = {item["person_id"]: item for item in package["activation_map"]}

    assert "person_bob" not in activation_map
    assert package["response_policy"]["mode"] == "single_primary"


def test_high_activation_barrier_limits_derived_latent_budget(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    group_id = create_group(
        db_path=db_path,
        group_type="team",
        name="核心团队",
        summary="主开发小组",
    )
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_alice", role_label="owner")
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_bob", role_label="member")
    add_group_member(db_path=db_path, group_id=group_id, person_id="person_carla", role_label="member")

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, summary, persona_summary, work_summary,
            life_summary, style_summary, boundary_summary, confidence, metadata_json,
            created_at, updated_at
        ) VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now')),
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now')),
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        (
            "person_alice", "Alice", "active", None, None, None, None, None, None, 0.8, "{}",
            "person_bob", "Bob", "active", None, None, None, None, None, None, 0.8, "{}",
            "person_carla", "Carla", "active", None, None, None, None, None, None, 0.8, "{}",
        ),
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="work_discussion",
        scene_summary="high barrier team sync",
        environment={
            "location_scope": "remote",
            "channel_scope": "group_channel",
            "visibility_scope": "group_visible",
            "activation_barrier": "high",
        },
        group_id=group_id,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)

    latent_ids = [
        item["person_id"]
        for item in package["activation_map"]
        if item["activation_state"] == "latent"
    ]
    budget = package["safety_and_budget"]["activation_budget"]

    assert len(latent_ids) == 1
    assert budget["max_derived_latent"] == 1
    assert budget["used_derived_latent"] == 1
    assert budget["blocked_derived_latent"] == 1


def test_relation_participants_activation_latent_by_default(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    people = {
        row[1]: row[0]
        for row in conn.execute("SELECT person_id, primary_name FROM persons").fetchall()
    }
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="relation latent test",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
            "activation_barrier": "low",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小王"],
        activation_state="explicit",
        activation_score=0.9,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    activation_map = {item["person_id"]: item for item in package["activation_map"]}

    relation_partner = people["小李"]
    assert relation_partner in activation_map
    assert activation_map[relation_partner]["activation_state"] == "latent"
    assert package["response_policy"]["mode"] == "single_primary"


def test_relation_participants_blocked_when_activation_barrier_strict(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    people = {
        row[1]: row[0]
        for row in conn.execute("SELECT person_id, primary_name FROM persons").fetchall()
    }
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="relation strict barrier",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
            "activation_barrier": "strict",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小王"],
        activation_state="explicit",
        activation_score=0.9,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    activation_map = {item["person_id"]: item for item in package["activation_map"]}

    relation_partner = people["小李"]
    assert relation_partner not in activation_map
    assert package["response_policy"]["mode"] == "single_primary"


def test_event_participants_trigger_additional_latent_activation(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="event activation",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=0.9,
        is_speaking=True,
    )

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO events(event_id, event_type, source_type, timestamp, summary, visibility_level, confidence, is_structured, raw_evidence_refs_json, metadata_json, created_at)
        VALUES(?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        [
            (
                "evt_extra",
                "dialogue_event",
                "system",
                "event triggered activation",
                1.0,
                0,
                1,
                "[]",
                "{}",
            ),
        ],
    )
    conn.executemany(
        """
        INSERT INTO event_participants(event_id, person_id, participant_role)
        VALUES(?, ?, ?)
        """,
        [
            ("evt_extra", "person_alice", "speaker"),
            ("evt_extra", "person_bob", "mentioned"),
        ],
    )
    conn.commit()
    conn.close()

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    activation_map = {item["person_id"]: item for item in package["activation_map"]}

    assert "person_bob" in activation_map
    assert activation_map["person_bob"]["activation_state"] == "latent"
    assert package["response_policy"]["mode"] == "single_primary"
    budget = package["safety_and_budget"]["activation_budget"]
    assert budget["used_event_latent"] == 1
    assert package["safety_and_budget"]["propagation_depth"] == 2


def test_event_budget_report_includes_weights(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="work_discussion",
        scene_summary="event budget",
        environment={
            "location_scope": "remote",
            "channel_scope": "group_channel",
            "visibility_scope": "group_visible",
            "activation_barrier": "medium",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO events(event_id, event_type, source_type, timestamp, summary, visibility_level, confidence, is_structured, raw_evidence_refs_json, metadata_json, created_at)
        VALUES(?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        [
            (
                "evt_event_budget",
                "dialogue_event",
                "system",
                "event drives budget",
                1.0,
                0,
                1,
                "[]",
                "{}",
            ),
        ],
    )
    conn.executemany(
        """
        INSERT INTO event_participants(event_id, person_id, participant_role)
        VALUES(?, ?, ?)
        """,
        [
            ("evt_event_budget", "person_alice", "speaker"),
            ("evt_event_budget", "person_bob", "mentioned"),
        ],
    )
    conn.commit()
    conn.close()

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    budget = package["safety_and_budget"]["activation_budget"]

    assert budget["max_derived_latent"] >= 1
    assert budget["event_weight"] == 0.8
    assert package["safety_and_budget"]["source_weights"]["event"] == 0.8
    assert package["safety_and_budget"]["event_decay_days"] == 30
    assert package["safety_and_budget"]["source_counts"]["event"]["used"] == 1


def test_runtime_reports_open_local_branch_risk(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="branch risk",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_branch",
            target_type="local_branch",
            target_id="branch_runtime_1",
            operation="create_local_branch",
            payload={
                "branch_id": "branch_runtime_1",
                "scope_type": "scene",
                "scope_id": scene_id,
                "status": "open",
                "reason": "ambiguous scene reading",
                "created_from_event_id": "evt_branch",
                "branch_candidates": [
                    {
                        "candidate_id": "candidate_scene_a",
                        "label": "私聊解读 A",
                        "payload_json": {"variant": "a"},
                        "confidence": 0.6,
                        "status": "open",
                    },
                    {
                        "candidate_id": "candidate_scene_b",
                        "label": "私聊解读 B",
                        "payload_json": {"variant": "b"},
                        "confidence": 0.7,
                        "status": "open",
                    },
                ],
            },
            confidence=0.6,
            reason="open branch",
        ),
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)

    assert package["safety_and_budget"]["open_local_branch_count"] == 1
    assert package["safety_and_budget"]["open_local_branch_ids"] == ["branch_runtime_1"]
    assert package["safety_and_budget"]["open_local_branch_candidate_count"] == 2


def test_old_event_participants_receive_decay_limited_activation(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="old event activation",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
            "activation_barrier": "low",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_alice",
        activation_state="explicit",
        activation_score=0.9,
        is_speaking=True,
    )

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO events(event_id, event_type, source_type, timestamp, summary, visibility_level, confidence, is_structured, raw_evidence_refs_json, metadata_json, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """,
        (
            "evt_old",
            "dialogue_event",
            "system",
            "2024-01-01T00:00:00+00:00",
            "old event activation",
            "visible",
            1.0,
            0,
            "[]",
            "{}",
        ),
    )
    conn.executemany(
        """
        INSERT INTO event_participants(event_id, person_id, participant_role)
        VALUES(?, ?, ?)
        """,
        [
            ("evt_old", "person_alice", "speaker"),
            ("evt_old", "person_bob", "mentioned"),
        ],
    )
    conn.commit()
    conn.close()

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    activation_map = {item["person_id"]: item for item in package["activation_map"]}

    assert activation_map["person_bob"]["activation_state"] == "latent"
    assert activation_map["person_bob"]["activation_score"] < 0.5


def test_text_chat_imported_relations_are_visible_in_runtime_retrieval(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    transcript = """2026-04-06 23:10 小王: 今天好累
2026-04-06 23:11 小李: 早点休息
"""
    ingest_text_chat(
        db_path=db_path,
        transcript=transcript,
        source_name="chat.txt",
    )

    conn = sqlite3.connect(db_path)
    people = {
        row[1]: row[0]
        for row in conn.execute("SELECT person_id, primary_name FROM persons").fetchall()
    }
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="text chat retrieval",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小王"],
        activation_state="explicit",
        activation_score=0.95,
        is_speaking=True,
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id=people["小李"],
        activation_state="latent",
        activation_score=0.75,
        is_speaking=False,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)

    relation_ids = {item["relation_id"] for item in package["active_relations"]}
    assert relation_ids


def test_retrieval_package_participants_include_persona_and_style(temp_project_with_migrations):
    """检索包 participants 应包含 persona_summary 和 style_summary。"""
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
        (
            "person_persona_test",
            "PersonaTest",
            "active",
            "测试摘要",
            "内向安静",
            "后端开发",
            None,
            "说话简洁",
            "不喜欢被打断",
            0.8,
            "{}",
        ),
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="persona test",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_persona_test",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    participant = package["participants"][0]

    assert participant["persona_summary"] == "内向安静"
    assert participant["style_summary"] == "说话简洁"
    assert participant["boundary_summary"] == "不喜欢被打断"


def test_retrieval_cache_default_ttl_writes_expires_at(temp_project_with_migrations):
    """不传 cache_ttl_seconds 时，使用默认 TTL，缓存行写入 expires_at 非 NULL。"""
    from we_together.runtime.sqlite_retrieval import DEFAULT_CACHE_TTL_SECONDS

    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="default ttl scene",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_default_ttl",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_default_ttl",
    )

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT expires_at FROM retrieval_cache WHERE scene_id = ? AND input_hash = ?",
        (scene_id, "hash_default_ttl"),
    ).fetchone()
    conn.close()

    assert row is not None
    assert row[0] is not None, "expires_at should not be NULL when default TTL is used"


def test_retrieval_cache_custom_ttl_respected(temp_project_with_migrations):
    """传 cache_ttl_seconds=3600 时，expires_at 约为 1 小时后。"""
    from datetime import datetime, UTC, timedelta

    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="custom ttl scene",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_custom_ttl",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    before = datetime.now(UTC)
    build_runtime_retrieval_package_from_db(
        db_path=db_path,
        scene_id=scene_id,
        input_hash="hash_custom_ttl",
        cache_ttl_seconds=3600,
    )
    after = datetime.now(UTC)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT expires_at FROM retrieval_cache WHERE scene_id = ? AND input_hash = ?",
        (scene_id, "hash_custom_ttl"),
    ).fetchone()
    conn.close()

    assert row is not None
    expires_at = datetime.fromisoformat(row[0])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    expected_low = before + timedelta(seconds=3600)
    expected_high = after + timedelta(seconds=3600)
    assert expected_low <= expires_at <= expected_high


def test_build_retrieval_package_rejects_closed_scene(temp_project_with_migrations):
    """对已关闭场景调用 retrieval 应抛 ValueError。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="closed scene",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )

    close_scene(db_path, scene_id)

    with pytest.raises(ValueError, match="not active"):
        build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)


def test_retrieval_package_respects_memory_limit(temp_project_with_migrations):
    """创建 10 条 memory，传 max_memories=3，验证返回最多 3 条。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    person_id = "person_mem_limit"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
        """,
        (person_id, "MemLimiter"),
    )
    for i in range(10):
        conn.execute(
            """
            INSERT INTO memories(
                memory_id, memory_type, summary, relevance_score, confidence,
                is_shared, status, metadata_json, created_at, updated_at
            ) VALUES(?, 'shared_memory', ?, ?, 0.7, 1, 'active', '{}', datetime('now'), datetime('now'))
            """,
            (f"mem_limit_{i}", f"memory {i}", 0.5 + i * 0.01),
        )
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) VALUES(?, 'person', ?, NULL)",
            (f"mem_limit_{i}", person_id),
        )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="memory limit test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id=person_id, activation_state="explicit", activation_score=1.0, is_speaking=True)

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id, max_memories=3)
    assert len(package["relevant_memories"]) == 3


def test_retrieval_package_respects_relation_limit(temp_project_with_migrations):
    """验证 max_relations 限制。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    person_a = "person_rel_limit_a"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, 'RelLimiterA', 'active', 0.8, '{}', datetime('now'), datetime('now'))
        """,
        (person_a,),
    )
    event_id = "evt_rel_limit"
    conn.execute(
        """
        INSERT INTO events(
            event_id, event_type, source_type, timestamp, summary, visibility_level,
            confidence, is_structured, raw_evidence_refs_json, metadata_json, created_at
        ) VALUES(?, 'narration_seed', 'manual', datetime('now'), 'relations', 'visible', 0.8, 0, '[]', '{}', datetime('now'))
        """,
        (event_id,),
    )
    conn.execute(
        "INSERT INTO event_participants(event_id, person_id, participant_role) VALUES(?, ?, 'speaker')",
        (event_id, person_a),
    )
    for i in range(5):
        rid = f"rel_limit_{i}"
        other = f"person_rel_other_{i}"
        conn.execute(
            """
            INSERT INTO persons(
                person_id, primary_name, status, confidence, metadata_json,
                created_at, updated_at
            ) VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
            """,
            (other, f"Other{i}"),
        )
        conn.execute(
            """
            INSERT INTO relations(
                relation_id, core_type, custom_label, summary, directionality,
                strength, stability, visibility, status, confidence, metadata_json,
                created_at, updated_at
            ) VALUES(?, 'friendship', ?, 'rel', 'bidirectional', 0.5, 0.5, 'known', 'active', 0.7, '{}', datetime('now'), datetime('now'))
            """,
            (rid, f"relation {i}"),
        )
        conn.execute(
            "INSERT INTO event_targets(event_id, target_type, target_id, impact_hint) VALUES(?, 'relation', ?, 'test')",
            (event_id, rid),
        )
        conn.execute(
            "INSERT INTO event_participants(event_id, person_id, participant_role) VALUES(?, ?, 'mentioned')",
            (event_id, other),
        )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="relation limit test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id=person_a, activation_state="explicit", activation_score=1.0, is_speaking=True)

    package = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id, max_relations=2)
    assert len(package["active_relations"]) == 2


def test_retrieval_package_includes_recent_changes(temp_project_with_migrations):
    """应用几个 patch 后，构建检索包应包含 recent_changes 字段。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="recent changes test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id="person_rc", activation_state="explicit", activation_score=1.0, is_speaking=True)

    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_rc_1",
            target_type="state",
            target_id="state_rc_1",
            operation="update_state",
            payload={
                "state_id": "state_rc_1",
                "scope_type": "scene",
                "scope_id": scene_id,
                "state_type": "mood",
                "value_json": {"mood": "happy"},
            },
            confidence=0.8,
            reason="recent change 1",
        ),
    )
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_rc_2",
            target_type="state",
            target_id="state_rc_2",
            operation="update_state",
            payload={
                "state_id": "state_rc_2",
                "scope_type": "scene",
                "scope_id": scene_id,
                "state_type": "energy",
                "value_json": {"energy": "high"},
            },
            confidence=0.7,
            reason="recent change 2",
        ),
    )

    package = build_runtime_retrieval_package_from_db(
        db_path=db_path, scene_id=scene_id, max_recent_changes=5,
    )

    assert "recent_changes" in package
    assert len(package["recent_changes"]) == 2
    assert package["recent_changes"][0]["operation"] == "update_state"


def test_retrieval_recent_changes_respects_limit(temp_project_with_migrations):
    """max_recent_changes 应控制返回条数。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="rc limit test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id="person_rcl", activation_state="explicit", activation_score=1.0, is_speaking=True)

    for i in range(5):
        apply_patch_record(
            db_path=db_path,
            patch=build_patch(
                source_event_id=f"evt_rcl_{i}",
                target_type="state",
                target_id=f"state_rcl_{i}",
                operation="update_state",
                payload={
                    "state_id": f"state_rcl_{i}",
                    "scope_type": "scene",
                    "scope_id": scene_id,
                    "state_type": "mood",
                    "value_json": {"mood": f"mood_{i}"},
                },
                confidence=0.7,
                reason=f"change {i}",
            ),
        )

    package = build_runtime_retrieval_package_from_db(
        db_path=db_path, scene_id=scene_id, max_recent_changes=2,
    )

    assert len(package["recent_changes"]) == 2
