import json
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.runtime.sqlite_retrieval import build_runtime_retrieval_package_from_db
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.scene_service import create_scene, add_scene_participant


def _add_person(db_path, person_id, name):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(
            person_id, primary_name, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
        """,
        (person_id, name),
    )
    conn.commit()
    conn.close()


def test_upsert_facet_patch_creates_row(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_f1", "Facey")

    patch = build_patch(
        source_event_id="evt_facet",
        target_type="person_facet",
        target_id="person_f1",
        operation="upsert_facet",
        payload={
            "person_id": "person_f1",
            "facet_type": "work",
            "facet_key": "role",
            "facet_value": "engineer",
            "confidence": 0.8,
            "scope_hint": "team",
        },
        confidence=0.8,
        reason="extract",
    )
    apply_patch_record(db_path=db_path, patch=patch)

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT facet_value_json, confidence FROM person_facets WHERE person_id = 'person_f1'",
    ).fetchone()
    conn.close()
    payload = json.loads(row[0])
    assert payload["value"] == "engineer"
    assert payload["scope_hint"] == "team"
    assert row[1] == 0.8


def test_upsert_facet_patch_replaces_existing(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_f2", "Facey2")

    for val, conf in [("junior", 0.5), ("senior", 0.9)]:
        apply_patch_record(
            db_path=db_path,
            patch=build_patch(
                source_event_id=f"evt_{val}",
                target_type="person_facet",
                target_id="person_f2",
                operation="upsert_facet",
                payload={
                    "person_id": "person_f2",
                    "facet_type": "work",
                    "facet_key": "role",
                    "facet_value": val,
                    "confidence": conf,
                },
                confidence=conf,
                reason="upsert",
            ),
        )

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT facet_value_json, confidence FROM person_facets WHERE person_id = 'person_f2'",
    ).fetchall()
    conn.close()
    assert len(rows) == 1
    payload = json.loads(rows[0][0])
    assert payload["value"] == "senior"
    assert rows[0][1] == 0.9


def test_retrieval_package_projects_facets_by_scene_type(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_proj", "Projector")

    # 灌入 work 和 life 两种 facet
    for ftype, key, val in [
        ("work", "role", "engineer"),
        ("life", "hobby", "diving"),
        ("persona", "tone", "calm"),
    ]:
        apply_patch_record(
            db_path=db_path,
            patch=build_patch(
                source_event_id=f"evt_{ftype}",
                target_type="person_facet",
                target_id="person_proj",
                operation="upsert_facet",
                payload={
                    "person_id": "person_proj",
                    "facet_type": ftype,
                    "facet_key": key,
                    "facet_value": val,
                    "confidence": 0.8,
                },
                confidence=0.8,
                reason="seed",
            ),
        )

    # work_discussion 应投影 work/style
    scene_work = create_scene(
        db_path=db_path, scene_type="work_discussion", scene_summary="work",
        environment={"location_scope": "remote", "channel_scope": "group_channel", "visibility_scope": "group_visible"},
    )
    add_scene_participant(
        db_path=db_path, scene_id=scene_work, person_id="person_proj",
        activation_state="explicit", activation_score=1.0, is_speaking=True,
    )
    pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_work)
    proj_types = {f["facet_type"] for f in pkg["participants"][0]["projected_facets"]}
    assert "work" in proj_types
    assert "life" not in proj_types

    # private_chat 应投影 persona/style/life/boundary
    scene_private = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="p",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(
        db_path=db_path, scene_id=scene_private, person_id="person_proj",
        activation_state="explicit", activation_score=1.0, is_speaking=True,
    )
    pkg2 = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_private)
    proj_types2 = {f["facet_type"] for f in pkg2["participants"][0]["projected_facets"]}
    assert "persona" in proj_types2
    assert "life" in proj_types2
    assert "work" not in proj_types2
