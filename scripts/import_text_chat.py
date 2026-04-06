from pathlib import Path
import sys
import argparse
import json


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.ingestion_service import ingest_text_chat


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import text chat transcript into the SQLite graph")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--transcript", required=True)
    parser.add_argument("--source-name", required=True)
    args = parser.parse_args()

    db_path = Path(args.root) / "db" / "main.sqlite3"
    result = ingest_text_chat(db_path=db_path, transcript=args.transcript, source_name=args.source_name)
    print(json.dumps(result, ensure_ascii=False))
