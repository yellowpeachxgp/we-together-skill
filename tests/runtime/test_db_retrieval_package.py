from we_together.db.bootstrap import bootstrap_project
from we_together.runtime.sqlite_retrieval import build_runtime_retrieval_package_from_db
from we_together.services.scene_service import create_scene, add_scene_participant
from we_together.services.ingestion_service import ingest_narration
import sqlite3


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

    display_names = {item["display_name"] for item in package["participants"]}
    assert "小王" in display_names
    assert "小李" in display_names
    assert len(package["active_relations"]) >= 1
    assert len(package["relevant_memories"]) >= 1
