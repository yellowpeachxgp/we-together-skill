from pathlib import Path
import sys
import argparse
import json
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def build_graph_summary(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    relation_count = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
    scene_count = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    people = [row[0] for row in conn.execute("SELECT primary_name FROM persons ORDER BY primary_name").fetchall()]
    conn.close()
    return {
        "person_count": person_count,
        "relation_count": relation_count,
        "scene_count": scene_count,
        "event_count": event_count,
        "people": people,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Summarize graph contents from SQLite")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    args = parser.parse_args()

    db_path = Path(args.root) / "db" / "main.sqlite3"
    print(json.dumps(build_graph_summary(db_path), ensure_ascii=False))
