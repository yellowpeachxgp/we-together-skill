from pathlib import Path
import tempfile
import shutil

import pytest


@pytest.fixture
def temp_project_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


@pytest.fixture
def temp_project_with_migrations(temp_project_dir):
    repo_root = Path(__file__).resolve().parents[1]
    source_dir = repo_root / "db" / "migrations"
    target_dir = temp_project_dir / "db" / "migrations"
    target_dir.mkdir(parents=True, exist_ok=True)
    for sql_file in source_dir.glob("*.sql"):
        shutil.copy2(sql_file, target_dir / sql_file.name)
    return temp_project_dir
