"""scripts/rollback_tick.py — 把图谱回滚到指定 tick snapshot。

用法:
  python scripts/rollback_tick.py --root . --snapshot snap_tick_3_1234567890

作用: 委派到 services.time_simulator.rollback_to_tick（后者复用 snapshot_service）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.tenant_router import resolve_tenant_root
from we_together.services.time_simulator import rollback_to_tick


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--snapshot", required=True)
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    if not db.exists():
        print(json.dumps({"error": "db not found"}))
        return 1

    try:
        r = rollback_to_tick(db, snapshot_id=args.snapshot)
        print(json.dumps(r or {"ok": True}, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
