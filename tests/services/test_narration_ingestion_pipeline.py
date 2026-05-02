import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.ingestion_service import ingest_narration


def test_ingest_narration_creates_import_job_evidence_event_patch_and_snapshot(
    temp_project_with_migrations,
):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    result = ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    counts = {
        "import_jobs": conn.execute("SELECT COUNT(*) FROM import_jobs").fetchone()[0],
        "raw_evidences": conn.execute("SELECT COUNT(*) FROM raw_evidences").fetchone()[0],
        "identity_links": conn.execute("SELECT COUNT(*) FROM identity_links").fetchone()[0],
        "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "patches": conn.execute("SELECT COUNT(*) FROM patches").fetchone()[0],
        "snapshots": conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
        "snapshot_entities": conn.execute("SELECT COUNT(*) FROM snapshot_entities").fetchone()[0],
        "memories": conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
    }
    conn.close()

    assert result["import_job_id"].startswith("import_")
    assert counts["import_jobs"] == 1
    assert counts["raw_evidences"] == 1
    assert counts["identity_links"] == 2
    assert counts["events"] == 1
    assert counts["patches"] >= 2
    assert counts["snapshots"] == 1
    assert counts["snapshot_entities"] >= 4
    assert counts["memories"] == 1


def test_ingest_narration_derives_people_and_relations(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    person_names = {
        row[0] for row in conn.execute("SELECT primary_name FROM persons").fetchall()
    }
    relation_rows = conn.execute(
        "SELECT core_type, custom_label FROM relations"
    ).fetchall()
    conn.close()

    assert "小王" in person_names
    assert "小李" in person_names
    assert len(relation_rows) >= 1


def test_ingest_narration_applies_inferred_patches_and_entity_links(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    ingest_narration(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    conn = sqlite3.connect(db_path)
    patch_operations = {
        row[0] for row in conn.execute("SELECT operation FROM patches").fetchall()
    }
    entity_link_count = conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    relation_state_count = conn.execute(
        "SELECT COUNT(*) FROM states WHERE scope_type = 'relation'"
    ).fetchone()[0]
    conn.close()

    assert "create_memory" in patch_operations
    assert "link_entities" in patch_operations
    assert "update_state" in patch_operations
    assert entity_link_count >= 1
    assert relation_state_count >= 1
