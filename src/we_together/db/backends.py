"""DB backend Protocol：SQLite / PG 可替换。

当前默认走 SQLite（已有 db/connection.py）。PG backend 是 stub，延迟 import
psycopg 只在实例化时加载。本 Protocol 不影响现有 service：所有代码仍然直接
用 `we_together.db.connection.connect(db_path)` 调 SQLite；只有 VI-6 希望
未来 refactor 时能统一口径。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol


class DBBackend(Protocol):
    name: str

    def connect(self, target: str) -> sqlite3.Connection: ...


class SQLiteBackend:
    name = "sqlite"

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def connect(self, target: str | None = None) -> sqlite3.Connection:
        from we_together.db.connection import connect
        return connect(self.db_path)


class PGBackend:  # pragma: no cover
    """PG backend stub：延迟 import psycopg。

    真实实现需要 schema 重写（BLOB → bytea，TEXT → varchar）+ psycopg DSN。
    当前只保留入口，供 Phase 30+ 扩展。
    """
    name = "postgres"

    def __init__(self, *, dsn: str):
        try:
            import psycopg  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "psycopg 未安装: pip install psycopg"
            ) from exc
        self.dsn = dsn

    def connect(self, target: str | None = None):
        import psycopg
        return psycopg.connect(self.dsn)
