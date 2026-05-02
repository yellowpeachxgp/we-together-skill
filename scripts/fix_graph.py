"""scripts/fix_graph.py — CLI 调 self_repair。

用法:
  python scripts/fix_graph.py --root . --policy report_only
  python scripts/fix_graph.py --root . --policy propose
  python scripts/fix_graph.py --root . --policy auto
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.self_repair import self_repair
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--policy", choices=["report_only", "propose", "auto"],
                    default="report_only")
    args = ap.parse_args()
    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    if not db.exists():
        print(json.dumps({"error": "db not found"}))
        return 1
    result = self_repair(db, policy=args.policy)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
