from pathlib import Path
import sys
import argparse
import json


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.auto_ingestion_service import auto_ingest_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automatically detect and import text into the SQLite graph")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--text", required=True)
    parser.add_argument("--source-name", required=True)
    args = parser.parse_args()

    db_path = Path(args.root) / "db" / "main.sqlite3"
    result = auto_ingest_text(db_path=db_path, text=args.text, source_name=args.source_name)
    print(json.dumps(result, ensure_ascii=False))
