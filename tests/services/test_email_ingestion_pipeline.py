import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.email_ingestion_service import ingest_email_file


def test_ingest_email_file_creates_person_event_and_snapshot(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    eml_path = tmp_path / "sample.eml"
    eml_path.write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Project Update\n"
        "Date: Mon, 06 Apr 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "今天的项目推进顺利。\n",
        encoding="utf-8",
    )

    result = ingest_email_file(db_path=db_path, email_path=eml_path)

    conn = sqlite3.connect(db_path)
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    identity_count = conn.execute("SELECT COUNT(*) FROM identity_links").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    snapshot_count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    snapshot_entity_count = conn.execute("SELECT COUNT(*) FROM snapshot_entities").fetchone()[0]
    conn.close()

    assert result["import_job_id"].startswith("import_")
    assert person_count >= 1
    assert identity_count >= 1
    assert event_count >= 1
    assert snapshot_count >= 1
    assert snapshot_entity_count >= 3


def test_ingest_email_file_infers_shared_memory_and_links(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    eml_path = tmp_path / "sample.eml"
    eml_path.write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Project Update\n"
        "Date: Mon, 06 Apr 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "今天的项目推进顺利。\n",
        encoding="utf-8",
    )

    ingest_email_file(db_path=db_path, email_path=eml_path)

    conn = sqlite3.connect(db_path)
    patch_operations = {
        row[0] for row in conn.execute("SELECT operation FROM patches").fetchall()
    }
    memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    entity_link_count = conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    person_state_count = conn.execute(
        "SELECT COUNT(*) FROM states WHERE scope_type = 'person'"
    ).fetchone()[0]
    conn.close()

    assert "create_memory" in patch_operations
    assert "link_entities" in patch_operations
    assert "update_state" in patch_operations
    assert memory_count >= 1
    assert entity_link_count >= 1
    assert person_state_count >= 1
