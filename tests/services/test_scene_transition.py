import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.group_service import add_group_member, create_group
from we_together.services.scene_service import add_scene_participant, create_scene
from we_together.services.scene_transition_service import suggest_next_scenes


def _add_person(db_path, pid, name):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json,
                            created_at, updated_at)
        VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
        """,
        (pid, name),
    )
    conn.commit()
    conn.close()


def test_suggest_switches_scene_type(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_tp_a", "A")
    _add_person(db_path, "person_tp_b", "B")

    sid = create_scene(
        db_path=db_path, scene_type="work_discussion", scene_summary="sync",
        environment={"location_scope": "remote", "channel_scope": "group_channel",
                     "visibility_scope": "group_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_tp_a",
                          activation_state="explicit", activation_score=1.0, is_speaking=True)
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_tp_b",
                          activation_state="latent", activation_score=0.7, is_speaking=False)

    sugg = suggest_next_scenes(db_path, sid, limit=5)
    kinds = {s["kind"] for s in sugg}
    types = {s["scene_type"] for s in sugg}
    assert "same_participants_new_type" in kinds
    assert "casual_social" in types or "private_chat" in types


def test_suggest_expands_group(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_g1", "G1")
    _add_person(db_path, "person_g2", "G2")
    _add_person(db_path, "person_g3", "G3")

    gid = create_group(db_path=db_path, group_type="team", name="X", summary="")
    add_group_member(db_path=db_path, group_id=gid, person_id="person_g1", role_label="owner")
    add_group_member(db_path=db_path, group_id=gid, person_id="person_g2", role_label="member")
    add_group_member(db_path=db_path, group_id=gid, person_id="person_g3", role_label="member")

    sid = create_scene(
        db_path=db_path, scene_type="work_discussion", scene_summary="sync",
        environment={"location_scope": "remote", "channel_scope": "group_channel",
                     "visibility_scope": "group_visible"},
        group_id=gid,
    )
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_g1",
                          activation_state="explicit", activation_score=1.0, is_speaking=True)

    sugg = suggest_next_scenes(db_path, sid, limit=5)
    expand = next((s for s in sugg if s["kind"] == "expand_group"), None)
    assert expand is not None
    assert len(expand["participant_person_ids"]) >= 2


def test_suggest_raises_for_missing_scene(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    import pytest
    with pytest.raises(ValueError):
        suggest_next_scenes(db_path, "scene_nope")
