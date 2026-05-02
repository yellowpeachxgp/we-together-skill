import json
from pathlib import Path

from we_together.db.connection import connect


def load_seed_files(db_path: Path, seeds_dir: Path) -> None:
    conn = connect(db_path)
    table_names = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }

    for seed_file in sorted(seeds_dir.glob("*.json")):
        payload = json.loads(seed_file.read_text(encoding="utf-8"))
        if "entity_tags" not in table_names:
            continue

        for row in payload.get("entity_tags", []):
            conn.execute(
                """
                INSERT INTO entity_tags(entity_type, entity_id, tag, weight)
                SELECT ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM entity_tags
                    WHERE entity_type = ?
                    AND entity_id = ?
                    AND tag = ?
                )
                """,
                (
                    row["entity_type"],
                    row["entity_id"],
                    row["tag"],
                    row.get("weight"),
                    row["entity_type"],
                    row["entity_id"],
                    row["tag"],
                ),
            )
    conn.commit()
    conn.close()
