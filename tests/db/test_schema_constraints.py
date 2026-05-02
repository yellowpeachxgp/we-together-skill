from pathlib import Path
import sqlite3

from we_together.db.migrator import run_migrations


ROOT = Path(__file__).resolve().parents[2]


def test_core_tables_exist_after_migration(temp_project_dir):
    db_path = temp_project_dir / "db" / "main.sqlite3"
    migrations_dir = temp_project_dir / "db" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    for src in (
        "db/migrations/0001_initial_core_schema.sql",
        "db/migrations/0002_connection_tables.sql",
        "db/migrations/0003_trace_and_evolution.sql",
        "db/migrations/0004_indexes_and_constraints.sql",
    ):
        source_path = ROOT / src
        target = migrations_dir / source_path.name
        target.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")

    run_migrations(db_path, migrations_dir)

    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()

    assert "persons" in tables
    assert "identity_links" in tables
    assert "events" in tables
    assert "patches" in tables
    assert "snapshots" in tables
