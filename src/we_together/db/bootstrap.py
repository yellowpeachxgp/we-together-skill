import shutil
from pathlib import Path

from we_together.db.migrator import run_migrations
from we_together.db.schema_version import check_schema_version
from we_together.db.seeds import load_seed_files

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


REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLED_ASSET_DIRS = {
    "db/migrations": REPO_ROOT / "db" / "migrations",
    "db/seeds": REPO_ROOT / "db" / "seeds",
}


def bootstrap_directories(root: Path) -> None:
    for rel_path in RUNTIME_DIRS:
        (root / rel_path).mkdir(parents=True, exist_ok=True)


def _provision_bundled_assets(root: Path) -> None:
    for rel_path, source_dir in BUNDLED_ASSET_DIRS.items():
        if not source_dir.exists():
            raise FileNotFoundError(f"Bundled asset directory not found: {source_dir}")

        target_dir = root / rel_path
        target_dir.mkdir(parents=True, exist_ok=True)
        existing_files = [path for path in target_dir.iterdir() if path.is_file()]
        if existing_files:
            continue

        for source_path in source_dir.iterdir():
            if not source_path.is_file():
                continue

            target_path = target_dir / source_path.name
            shutil.copy2(source_path, target_path)


def bootstrap_project(root: Path) -> None:
    bootstrap_directories(root)
    _provision_bundled_assets(root)
    db_path = root / "db" / "main.sqlite3"
    migrations_dir = root / "db" / "migrations"
    # 版本一致性预检：若 db 已存在且记录了本地缺失的 migration，立即报错
    check_schema_version(db_path, migrations_dir)
    run_migrations(db_path, migrations_dir)
    # Phase 27 PD-4: 启用 WAL 模式（并发读 + 更好的崩溃恢复）
    try:
        import sqlite3 as _sqlite3
        _conn = _sqlite3.connect(db_path)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.close()
    except Exception:
        pass
    seeds_dir = root / "db" / "seeds"
    load_seed_files(db_path, seeds_dir)
