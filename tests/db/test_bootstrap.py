from pathlib import Path
import subprocess

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


def test_bootstrap_script_runs_from_repo_root():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [str(repo_root / ".venv" / "bin" / "python"), "scripts/bootstrap.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "bootstrap complete" in result.stdout
