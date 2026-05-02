from pathlib import Path
import subprocess
import sys
import sqlite3

from we_together.db.bootstrap import bootstrap_directories, bootstrap_project


def test_bootstrap_directories_creates_runtime_layout(temp_project_dir):
    bootstrap_directories(temp_project_dir)

    assert (temp_project_dir / "db").exists()
    assert (temp_project_dir / "db" / "migrations").exists()
    assert (temp_project_dir / "db" / "seeds").exists()
    assert (temp_project_dir / "data").exists()
    assert (temp_project_dir / "data" / "raw").exists()
    assert (temp_project_dir / "data" / "derived").exists()
    assert (temp_project_dir / "data" / "snapshots").exists()
    assert (temp_project_dir / "data" / "runtime").exists()


def test_bootstrap_project_creates_database_and_runtime_dirs(temp_project_dir):
    migrations_dir = temp_project_dir / "db" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    (migrations_dir / "0001_init.sql").write_text(
        "CREATE TABLE sample(id TEXT PRIMARY KEY);",
        encoding="utf-8",
    )

    bootstrap_project(temp_project_dir)

    assert (temp_project_dir / "db" / "main.sqlite3").exists()
    assert (temp_project_dir / "data" / "raw").exists()


def test_bootstrap_project_uses_bundled_assets_when_root_has_no_migrations(temp_project_dir):
    bootstrap_project(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    table_names = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    entity_tag_count = conn.execute("SELECT COUNT(*) FROM entity_tags").fetchone()[0]
    conn.close()

    assert "persons" in table_names
    assert "scenes" in table_names
    assert "entity_tags" in table_names
    assert entity_tag_count > 0


def test_bootstrap_script_runs_from_repo_root():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [str(repo_root / ".venv" / "bin" / "python"), "scripts/bootstrap.py", "--root", str(repo_root)],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "bootstrap complete" in result.stdout


def test_bootstrap_script_bootstraps_empty_external_root(temp_project_dir):
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            str(repo_root / ".venv" / "bin" / "python"),
            "scripts/bootstrap.py",
            "--root",
            str(temp_project_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(temp_project_dir / "db" / "main.sqlite3")
    table_names = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    conn.close()

    assert "persons" in table_names
