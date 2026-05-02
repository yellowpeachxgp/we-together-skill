import json
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.dialogue_service import record_dialogue_event, process_dialogue_turn
from we_together.services.patch_service import infer_dialogue_patches
from we_together.services.patch_applier import apply_patch_record
from we_together.services.scene_service import create_scene, add_scene_participant


def test_record_dialogue_event_creates_event_and_participants(temp_project_with_migrations):
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
        ("person_dlg_a", "小明", "active", None, None, None, None, None, None, 0.8, "{}"),
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="dialogue test",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(
        db_path=db_path,
        scene_id=scene_id,
        person_id="person_dlg_a",
        activation_state="explicit",
        activation_score=1.0,
        is_speaking=True,
    )

    result = record_dialogue_event(
        db_path=db_path,
        scene_id=scene_id,
        user_input="今天心情怎么样？",
        response_text="挺好的，谢谢关心。",
        speaking_person_ids=["person_dlg_a"],
    )

    assert "event_id" in result
    assert result["event_type"] == "dialogue_event"

    conn = sqlite3.connect(db_path)
    event_row = conn.execute(
        "SELECT event_type, source_type, scene_id, summary FROM events WHERE event_id = ?",
        (result["event_id"],),
    ).fetchone()
    participant_rows = conn.execute(
        "SELECT person_id, participant_role FROM event_participants WHERE event_id = ?",
        (result["event_id"],),
    ).fetchall()
    conn.close()

    assert event_row[0] == "dialogue_event"
    assert event_row[1] == "dialogue"
    assert event_row[2] == scene_id
    assert len(participant_rows) >= 1
    assert participant_rows[0][1] == "speaker"


def test_record_dialogue_event_creates_snapshot(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="snapshot dialogue test",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )

    result = record_dialogue_event(
        db_path=db_path,
        scene_id=scene_id,
        user_input="你好",
        response_text="你好呀",
        speaking_person_ids=[],
    )

    assert result["snapshot_id"] is not None
    conn = sqlite3.connect(db_path)
    snap_row = conn.execute(
        "SELECT snapshot_id FROM snapshots WHERE snapshot_id = ?",
        (result["snapshot_id"],),
    ).fetchone()
    conn.close()
    assert snap_row is not None


def test_infer_dialogue_patches_creates_scene_state(temp_project_with_migrations):
    """对话 patch 推理应为场景生成 mood state。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="dialogue patch inference test",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )

    result = record_dialogue_event(
        db_path=db_path,
        scene_id=scene_id,
        user_input="最近工作很顺利",
        response_text="那太好了！",
        speaking_person_ids=[],
    )

    patches = infer_dialogue_patches(
        source_event_id=result["event_id"],
        scene_id=scene_id,
        user_input="最近工作很顺利",
        response_text="那太好了！",
        speaking_person_ids=[],
    )

    assert len(patches) >= 1
    state_patches = [p for p in patches if p["operation"] == "update_state"]
    assert len(state_patches) >= 1
    assert state_patches[0]["payload_json"]["scope_type"] == "scene"
    assert state_patches[0]["payload_json"]["scope_id"] == scene_id

    for p in patches:
        apply_patch_record(db_path=db_path, patch=p)

    conn = sqlite3.connect(db_path)
    state_row = conn.execute(
        "SELECT value_json FROM states WHERE scope_type = 'scene' AND scope_id = ?",
        (scene_id,),
    ).fetchone()
    conn.close()
    assert state_row is not None


def test_infer_dialogue_patches_creates_memory_for_speakers(temp_project_with_migrations):
    """对话 patch 推理应为有发言人的对话生成共享记忆。"""
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
        [("person_dlg_m1", "小红"), ("person_dlg_m2", "小蓝")],
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="memory dialogue test",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )

    result = record_dialogue_event(
        db_path=db_path,
        scene_id=scene_id,
        user_input="今天一起吃火锅吧",
        response_text="好啊，我也想吃！",
        speaking_person_ids=["person_dlg_m1", "person_dlg_m2"],
    )

    patches = infer_dialogue_patches(
        source_event_id=result["event_id"],
        scene_id=scene_id,
        user_input="今天一起吃火锅吧",
        response_text="好啊，我也想吃！",
        speaking_person_ids=["person_dlg_m1", "person_dlg_m2"],
    )

    memory_patches = [p for p in patches if p["operation"] == "create_memory"]
    assert len(memory_patches) >= 1
    assert memory_patches[0]["payload_json"]["is_shared"] == 1

    for p in patches:
        apply_patch_record(db_path=db_path, patch=p)


def test_process_dialogue_turn_returns_package_and_updates_graph(temp_project_with_migrations):
    """process_dialogue_turn 一键调用应返回检索包、event_id 和图谱更新。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="e2e dialogue turn",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )

    result = process_dialogue_turn(
        db_path=db_path,
        scene_id=scene_id,
        user_input="今天天气真好",
        response_text="确实不错！",
    )

    assert "retrieval_package" in result
    assert "event_id" in result
    assert result["applied_patch_count"] >= 1
    assert result["retrieval_package"]["scene_summary"]["scene_id"] == scene_id

    conn = sqlite3.connect(db_path)
    state_row = conn.execute(
        "SELECT 1 FROM states WHERE scope_type = 'scene' AND scope_id = ?",
        (scene_id,),
    ).fetchone()
    conn.close()
    assert state_row is not None


def test_process_dialogue_turn_with_speakers_creates_memory(temp_project_with_migrations):
    """有 speaking_person_ids 时 process_dialogue_turn 应创建共享记忆。"""
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
        [("person_turn_a", "小红"), ("person_turn_b", "小蓝")],
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="e2e with speakers",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id="person_turn_a", activation_state="explicit", activation_score=1.0, is_speaking=True)
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id="person_turn_b", activation_state="latent", activation_score=0.8, is_speaking=False)

    result = process_dialogue_turn(
        db_path=db_path,
        scene_id=scene_id,
        user_input="一起去看电影吧",
        response_text="好啊，什么时候？",
        speaking_person_ids=["person_turn_a", "person_turn_b"],
    )

    assert result["applied_patch_count"] >= 2  # state + memory

    conn = sqlite3.connect(db_path)
    memory_row = conn.execute(
        "SELECT 1 FROM memories WHERE status = 'active' AND is_shared = 1",
    ).fetchone()
    conn.close()
    assert memory_row is not None
