import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.auto_ingestion_service import auto_ingest_text
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Automatically detect and import text into the SQLite graph")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--text", required=True)
    parser.add_argument("--source-name", required=True)
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    result = auto_ingest_text(db_path=db_path, text=args.text, source_name=args.source_name)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
