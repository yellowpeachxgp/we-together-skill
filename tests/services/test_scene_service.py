import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.scene_service import create_scene, add_scene_participant


def test_create_scene_and_add_participant_persist_records(temp_project_with_migrations):
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

    conn = sqlite3.connect(db_path)
    scene_count = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    participant_count = conn.execute("SELECT COUNT(*) FROM scene_participants").fetchone()[0]
    conn.close()

    assert scene_count == 1
    assert participant_count == 1
