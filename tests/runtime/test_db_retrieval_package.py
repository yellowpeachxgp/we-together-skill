from we_together.db.bootstrap import bootstrap_project
from we_together.runtime.sqlite_retrieval import build_runtime_retrieval_package_from_db
from we_together.services.scene_service import create_scene, add_scene_participant


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
