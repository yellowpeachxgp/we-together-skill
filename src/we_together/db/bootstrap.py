from pathlib import Path

from we_together.db.migrator import run_migrations


RUNTIME_DIRS = [
    "db",
    "db/migrations",
    "db/seeds",
    "data",
    "data/raw",
    "data/derived",
    "data/snapshots",
    "data/runtime",
]


def bootstrap_directories(root: Path) -> None:
    for rel_path in RUNTIME_DIRS:
        (root / rel_path).mkdir(parents=True, exist_ok=True)


def bootstrap_project(root: Path) -> None:
    bootstrap_directories(root)
    db_path = root / "db" / "main.sqlite3"
    migrations_dir = root / "db" / "migrations"
    run_migrations(db_path, migrations_dir)
