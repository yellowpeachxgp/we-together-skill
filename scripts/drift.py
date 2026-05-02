import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.relation_drift_service import drift_relations
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="关系漂移：按 event 窗口重算 strength")
    parser.add_argument("--root", default=str(ROOT), help="db-backed project root")
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    project_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db_path = project_root / "db" / "main.sqlite3"
    result = drift_relations(db_path, window_days=args.window_days, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
