from pathlib import Path
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.file_ingestion_service import ingest_file_auto


def test_ingest_file_auto_routes_text_file(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    txt = tmp_path / "sample.txt"
    txt.write_text("小王和小李以前是同事，现在还是朋友。", encoding="utf-8")

    result = ingest_file_auto(db_path=db_path, file_path=txt)

    conn = sqlite3.connect(db_path)
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    conn.close()

    assert result["mode"] == "text"
    assert person_count >= 2


def test_ingest_file_auto_routes_email_file(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    eml = tmp_path / "sample.eml"
    eml.write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Project Update\n"
        "Date: Mon, 06 Apr 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "今天的项目推进顺利。\n",
        encoding="utf-8",
    )

    result = ingest_file_auto(db_path=db_path, file_path=eml)

    assert result["mode"] == "email"


def test_ingest_file_auto_inherits_email_state_inference(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    eml = tmp_path / "sample.eml"
    eml.write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Project Update\n"
        "Date: Mon, 06 Apr 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "今天的项目推进顺利。\n",
        encoding="utf-8",
    )

    ingest_file_auto(db_path=db_path, file_path=eml)

    conn = sqlite3.connect(db_path)
    state_count = conn.execute(
        "SELECT COUNT(*) FROM states WHERE scope_type = 'person'"
    ).fetchone()[0]
    conn.close()

    assert state_count >= 1


def test_ingest_file_auto_raises_clear_error_for_missing_file(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    missing_file = temp_project_with_migrations / "missing.txt"

    try:
        ingest_file_auto(db_path=db_path, file_path=missing_file)
    except FileNotFoundError as exc:
        assert str(exc) == f"File not found: {missing_file}"
    else:
        raise AssertionError("Expected FileNotFoundError for missing file")
