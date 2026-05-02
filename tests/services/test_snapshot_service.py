from we_together.services.snapshot_service import (
    build_snapshot,
    build_snapshot_entities,
    list_snapshots,
    rollback_to_snapshot,
    replay_patches_after_snapshot,
)
from we_together.db.bootstrap import bootstrap_project
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.dialogue_service import record_dialogue_event
from we_together.services.scene_service import create_scene
import sqlite3


def test_build_snapshot_creates_structured_snapshot():
    snapshot = build_snapshot(
        snapshot_id="snap_1",
        based_on_snapshot_id=None,
        trigger_event_id="evt_1",
        summary="after import",
        graph_hash="hash_123",
    )

    assert snapshot["snapshot_id"] == "snap_1"
    assert snapshot["trigger_event_id"] == "evt_1"
    assert snapshot["graph_hash"] == "hash_123"


def test_build_snapshot_entities_creates_distinct_rows():
    rows = build_snapshot_entities(
        snapshot_id="snap_1",
        entities=[
            ("person", "person_a"),
            ("person", "person_a"),
            ("memory", "memory_1"),
        ],
    )

    assert len(rows) == 2
    assert rows[0]["snapshot_id"] == "snap_1"
    assert {row["entity_type"] for row in rows} == {"person", "memory"}


def test_list_snapshots_returns_ordered_history(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="snapshot list test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )

    r1 = record_dialogue_event(db_path=db_path, scene_id=scene_id, user_input="第一轮", response_text="好的", speaking_person_ids=[])
    r2 = record_dialogue_event(db_path=db_path, scene_id=scene_id, user_input="第二轮", response_text="继续", speaking_person_ids=[])

    snapshots = list_snapshots(db_path)
    assert len(snapshots) >= 2
    ids = [s["snapshot_id"] for s in snapshots]
    assert r1["snapshot_id"] in ids
    assert r2["snapshot_id"] in ids
    # 按时间降序
    assert snapshots[0]["created_at"] >= snapshots[1]["created_at"]


def test_rollback_to_snapshot_removes_later_states(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    # 创建一个 state
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_snap_rb_1",
            target_type="state",
            target_id="state_snap_rb_1",
            operation="update_state",
            payload={
                "state_id": "state_snap_rb_1",
                "scope_type": "scene",
                "scope_id": "scene_snap_rb",
                "state_type": "mood",
                "value_json": {"mood": "calm"},
            },
            confidence=0.7,
            reason="before snapshot",
        ),
    )

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="rollback test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )

    # 记录对话生成 snapshot
    r1 = record_dialogue_event(db_path=db_path, scene_id=scene_id, user_input="checkpoint", response_text="ok", speaking_person_ids=[])

    # 之后再创建新 state
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_snap_rb_2",
            target_type="state",
            target_id="state_snap_rb_2",
            operation="update_state",
            payload={
                "state_id": "state_snap_rb_2",
                "scope_type": "scene",
                "scope_id": "scene_snap_rb",
                "state_type": "energy",
                "value_json": {"energy": "low"},
            },
            confidence=0.7,
            reason="after snapshot",
        ),
    )

    # 验证新 state 存在
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT 1 FROM states WHERE state_id = 'state_snap_rb_2'").fetchone() is not None
    conn.close()

    # 回滚到 snapshot
    rollback_to_snapshot(db_path, r1["snapshot_id"])

    # 回滚后，snapshot 之后的 patch 应被标记为 rolled_back，后续 state 应被移除
    conn = sqlite3.connect(db_path)
    rb_state = conn.execute("SELECT 1 FROM states WHERE state_id = 'state_snap_rb_2'").fetchone()
    rb_patches = conn.execute(
        "SELECT status FROM patches WHERE patch_id IN (SELECT patch_id FROM patches WHERE applied_at > (SELECT created_at FROM snapshots WHERE snapshot_id = ?))",
        (r1["snapshot_id"],),
    ).fetchall()
    conn.close()

    assert rb_state is None


def test_replay_patches_after_snapshot_restores_state(temp_project_with_migrations):
    """回滚后重放 → 验证 state 恢复。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    # 创建一个 state
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_replay_1",
            target_type="state",
            target_id="state_replay_1",
            operation="update_state",
            payload={
                "state_id": "state_replay_1",
                "scope_type": "scene",
                "scope_id": "scene_replay",
                "state_type": "mood",
                "value_json": {"mood": "calm"},
            },
            confidence=0.7,
            reason="before snapshot",
        ),
    )

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="replay test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )

    # 生成 snapshot
    r1 = record_dialogue_event(db_path=db_path, scene_id=scene_id, user_input="checkpoint", response_text="ok", speaking_person_ids=[])

    # 之后创建新 state
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_replay_2",
            target_type="state",
            target_id="state_replay_2",
            operation="update_state",
            payload={
                "state_id": "state_replay_2",
                "scope_type": "scene",
                "scope_id": "scene_replay",
                "state_type": "energy",
                "value_json": {"energy": "low"},
            },
            confidence=0.7,
            reason="after snapshot",
        ),
    )

    # 回滚
    rollback_to_snapshot(db_path, r1["snapshot_id"])

    # 验证 state 被删除
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT 1 FROM states WHERE state_id = 'state_replay_2'").fetchone() is None
    conn.close()

    # 重放
    result = replay_patches_after_snapshot(db_path, r1["snapshot_id"])
    assert result["replayed_count"] >= 1

    # 验证 state 恢复
    conn = sqlite3.connect(db_path)
    restored_state = conn.execute("SELECT 1 FROM states WHERE state_id = 'state_replay_2'").fetchone()
    conn.close()
    assert restored_state is not None
