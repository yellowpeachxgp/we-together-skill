from pathlib import Path
import sqlite3

from we_together.db.migrator import run_migrations


def test_run_migrations_creates_schema_migrations_and_applies_sql(temp_project_dir):
    db_path = temp_project_dir / "db" / "main.sqlite3"
    migrations_dir = temp_project_dir / "db" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    (migrations_dir / "0001_sample.sql").write_text(
        "CREATE TABLE sample(id INTEGER PRIMARY KEY);",
        encoding="utf-8",
    )

    run_migrations(db_path, migrations_dir)

    conn = sqlite3.connect(db_path)
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()

    assert "schema_migrations" in tables
    assert "sample" in tables
