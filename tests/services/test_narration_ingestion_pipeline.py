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
        "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "patches": conn.execute("SELECT COUNT(*) FROM patches").fetchone()[0],
        "snapshots": conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
        "memories": conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0],
    }
    conn.close()

    assert result["import_job_id"].startswith("import_")
    assert counts == {
        "import_jobs": 1,
        "raw_evidences": 1,
        "events": 1,
        "patches": 1,
        "snapshots": 1,
        "memories": 1,
    }


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
