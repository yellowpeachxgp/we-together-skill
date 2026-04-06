from pathlib import Path
import json

from we_together.db.connection import connect


def load_seed_files(db_path: Path, seeds_dir: Path) -> None:
    conn = connect(db_path)
    for seed_file in sorted(seeds_dir.glob("*.json")):
        payload = json.loads(seed_file.read_text(encoding="utf-8"))
        for row in payload.get("entity_tags", []):
            conn.execute(
                """
                INSERT INTO entity_tags(entity_type, entity_id, tag, weight)
                VALUES(?, ?, ?, ?)
                """,
                (
                    row["entity_type"],
                    row["entity_id"],
                    row["tag"],
                    row.get("weight"),
                ),
            )
    conn.commit()
    conn.close()
