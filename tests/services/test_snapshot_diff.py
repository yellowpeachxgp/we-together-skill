import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.dialogue_service import record_dialogue_event
from we_together.services.scene_service import create_scene
from we_together.services.snapshot_diff_service import diff_snapshots


def test_diff_snapshots_returns_patches_between(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    sid = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="d",
        environment={"location_scope": "remote", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible"},
    )
    r1 = record_dialogue_event(db_path=db_path, scene_id=sid,
                                user_input="a", response_text="b", speaking_person_ids=[])
    r2 = record_dialogue_event(db_path=db_path, scene_id=sid,
                                user_input="c", response_text="d", speaking_person_ids=[])

    result = diff_snapshots(db_path, r1["snapshot_id"], r2["snapshot_id"])
    assert result["from_snapshot_id"] == r1["snapshot_id"]
    assert "patch_count" in result


def test_diff_snapshots_raises_for_missing(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    import pytest
    with pytest.raises(ValueError):
        diff_snapshots(db_path, "nope1", "nope2")
