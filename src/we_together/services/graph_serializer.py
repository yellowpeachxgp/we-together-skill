"""Graph canonical 序列化：db ↔ canonical JSON，支持跨实例迁移。

schema v1:
{
  "format_version": 1,
  "exported_at": "...",
  "schema_version": "0012",
  "persons": [...],
  "relations": [...],
  "memories": [...],
  "memory_owners": [...],
  "scenes": [...],
  "scene_participants": [...],
  "events": [...],
  "event_participants": [...],
  "event_targets": [...]
}

不包括：patches / snapshots / retrieval_cache（运行时或留痕信息）
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.db.connection import connect

FORMAT_VERSION = 1

CORE_TABLES = [
    "persons", "relations", "memories", "memory_owners",
    "scenes", "scene_participants",
    "events", "event_participants", "event_targets",
]


def serialize_graph(db_path: Path) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    out: dict = {
        "format_version": FORMAT_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
    }
    # schema version
    try:
        row = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        ).fetchone()
        out["schema_version"] = row[0] if row else None
    except sqlite3.OperationalError:
        out["schema_version"] = None

    for table in CORE_TABLES:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            out[table] = [dict(r) for r in rows]
        except sqlite3.OperationalError:
            out[table] = []
    conn.close()
    return out


def deserialize_graph(data: dict, target_root: Path) -> dict:
    """从 canonical JSON bootstrap 新 db（target_root 必须为空或仅含 migrations）。"""
    bootstrap_project(target_root)
    db_path = target_root / "db" / "main.sqlite3"
    conn = connect(db_path)
    imported: dict[str, int] = {}
    for table in CORE_TABLES:
        rows = data.get(table) or []
        if not rows:
            imported[table] = 0
            continue
        cols = list(rows[0].keys())
        placeholders = ",".join("?" for _ in cols)
        cols_sql = ",".join(cols)
        for r in rows:
            try:
                conn.execute(
                    f"INSERT OR IGNORE INTO {table}({cols_sql}) VALUES({placeholders})",
                    tuple(r.get(c) for c in cols),
                )
            except sqlite3.IntegrityError:
                continue
        imported[table] = len(rows)
    conn.commit()
    conn.close()
    return {
        "target": str(db_path),
        "imported": imported,
        "format_version": data.get("format_version"),
    }


def dump_graph_to_file(db_path: Path, out_file: Path) -> dict:
    data = serialize_graph(db_path)
    out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    total_rows = sum(len(data.get(t) or []) for t in CORE_TABLES)
    return {"out": str(out_file), "row_count": total_rows}


def load_graph_from_file(in_file: Path, target_root: Path) -> dict:
    data = json.loads(in_file.read_text(encoding="utf-8"))
    return deserialize_graph(data, target_root)
