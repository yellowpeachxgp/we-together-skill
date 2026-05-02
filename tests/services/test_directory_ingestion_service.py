from pathlib import Path
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.directory_ingestion_service import ingest_directory


def test_ingest_directory_imports_supported_files(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    (tmp_path / "note.txt").write_text("小王和小李以前是同事，现在还是朋友。", encoding="utf-8")
    (tmp_path / "mail.eml").write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Project Update\n"
        "Date: Mon, 06 Apr 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "今天的项目推进顺利。\n",
        encoding="utf-8",
    )

    result = ingest_directory(db_path=db_path, directory=tmp_path)

    conn = sqlite3.connect(db_path)
    import_jobs = conn.execute("SELECT COUNT(*) FROM import_jobs").fetchone()[0]
    persons = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    conn.close()

    assert result["file_count"] == 2
    assert import_jobs >= 2
    assert persons >= 3


def test_ingest_directory_raises_clear_error_for_missing_directory(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    missing_dir = temp_project_with_migrations / "missing-dir"

    try:
        ingest_directory(db_path=db_path, directory=missing_dir)
    except FileNotFoundError as exc:
        assert str(exc) == f"Directory not found: {missing_dir}"
    else:
        raise AssertionError("Expected FileNotFoundError for missing directory")


def test_ingest_directory_reports_skipped_unsupported_files(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    (tmp_path / "note.txt").write_text("小王和小李以前是同事，现在还是朋友。", encoding="utf-8")
    (tmp_path / "ignored.png").write_bytes(b"not-a-real-png")

    result = ingest_directory(db_path=db_path, directory=tmp_path)

    assert result["file_count"] == 1
    assert result["skipped_count"] == 1
    assert result["skipped_files"] == ["ignored.png"]
