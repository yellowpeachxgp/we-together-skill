"""scripts/dream_cycle.py — 触发 dream cycle。

用法:
  python scripts/dream_cycle.py --root . [--lookback 30]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.dream_cycle import run_dream_cycle
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--lookback", type=int, default=30)
    ap.add_argument("--min-cluster", type=int, default=3)
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    if not db.exists():
        print(json.dumps({"error": "db not found"}))
        return 1

    r = run_dream_cycle(
        db, min_cluster_size=args.min_cluster,
        lookback_days=args.lookback,
        archive_low_relevance=not args.no_archive,
    )
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
