import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.db.bootstrap import bootstrap_project
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap we_together runtime directories and database")
    parser.add_argument("--root", default=str(ROOT), help="Project root for runtime data and database")
    parser.add_argument("--tenant-id", default=None, help="Optional tenant id")
    args = parser.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    bootstrap_project(tenant_root)
    print("bootstrap complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
