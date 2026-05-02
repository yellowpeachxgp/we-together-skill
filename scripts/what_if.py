"""scripts/what_if.py：社会模拟 teaser CLI。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.tenant_router import resolve_tenant_root
from we_together.simulation.what_if_service import simulate_what_if

ROOT_HELP = (
    "Project root containing db/main.sqlite3 "
    "or tenants/<tenant-id>/db/main.sqlite3"
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help=ROOT_HELP)
    ap.add_argument("--tenant-id", default=None, help="Optional tenant id")
    ap.add_argument("--scene-id", required=True)
    ap.add_argument("--hypothesis", required=True)
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    result = simulate_what_if(db_path=db, scene_id=args.scene_id,
                               hypothesis=args.hypothesis)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
