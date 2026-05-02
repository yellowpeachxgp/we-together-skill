from pathlib import Path

from we_together.db.connection import connect

MIGRATION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations(
    version TEXT PRIMARY KEY,
    description TEXT,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def run_migrations(db_path: Path, migrations_dir: Path) -> None:
    conn = connect(db_path)
    conn.execute(MIGRATION_TABLE_SQL)
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations").fetchall()}
    for path in sorted(migrations_dir.glob("*.sql")):
        version = path.stem.split("_", 1)[0]
        if version in applied:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations(version, description) VALUES(?, ?)",
            (version, path.name),
        )
    conn.commit()
    conn.close()
