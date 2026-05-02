import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.directory_ingestion_service import ingest_directory
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a directory of supported files into the SQLite graph")
    parser.add_argument("--root", default=str(ROOT), help="Project root containing db/main.sqlite3")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    directory = Path(args.dir)
    if not directory.exists() or not directory.is_dir():
        print(f"Directory not found: {directory}", file=sys.stderr)
        raise SystemExit(1)

    result = ingest_directory(db_path=db_path, directory=directory)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
