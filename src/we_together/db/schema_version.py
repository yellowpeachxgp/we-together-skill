"""Schema 版本检测：检查 db 记录的 migrations 与本地 migrations_dir 是否一致。

规则：
  - 如果 db 中有 applied migration 但本地 migrations_dir 找不到对应文件 → SchemaVersionError
  - 如果本地有新 migration 但 db 未 apply → warning（正常启动流程会 apply）

暴露一个 check_schema_version(db_path, migrations_dir) -> dict 函数。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.errors import SchemaVersionError


def _fetch_applied(db_path: Path) -> set[str]:
    if not db_path.exists():
        return set()
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()
        return {r[0] for r in rows}
    except sqlite3.OperationalError:
        return set()
    finally:
        conn.close()


def _list_local_migrations(migrations_dir: Path) -> set[str]:
    if not migrations_dir.exists():
        return set()
    return {p.stem.split("_", 1)[0] for p in sorted(migrations_dir.glob("*.sql"))}


def check_schema_version(db_path: Path, migrations_dir: Path) -> dict:
    applied = _fetch_applied(db_path)
    available = _list_local_migrations(migrations_dir)

    missing_local = sorted(applied - available)
    pending = sorted(available - applied)

    if missing_local:
        raise SchemaVersionError(
            f"DB has applied migrations not found locally: {missing_local}. "
            f"This usually means migration files were removed or the db is from a "
            f"newer schema version than the current code."
        )

    return {
        "applied": sorted(applied),
        "pending": pending,
        "latest_applied": sorted(applied)[-1] if applied else None,
        "latest_available": sorted(available)[-1] if available else None,
    }
