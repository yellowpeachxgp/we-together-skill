"""scripts/activation_path.py — CLI: 打印从 A 到 B 的激活路径。

用法:
  python scripts/activation_path.py --root . --from person_a --to person_b --max-hops 3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.activation_trace_service import (
    multi_hop_activation,
    query_path,
)
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--to", dest="dst", default=None,
                    help="if omitted: show multi-hop activation map from src")
    ap.add_argument("--max-hops", type=int, default=3)
    ap.add_argument("--decay", type=float, default=0.5)
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    if not db.exists():
        print(json.dumps({"error": "db not found"}))
        return 1

    if args.dst:
        paths = query_path(
            db, from_entity_id=args.src, to_entity_id=args.dst,
            max_hops=args.max_hops,
        )
        print(json.dumps(
            {"paths": paths, "count": len(paths)},
            ensure_ascii=False, indent=2,
        ))
    else:
        m = multi_hop_activation(
            db, start_entity_id=args.src, max_hops=args.max_hops, decay=args.decay,
        )
        print(json.dumps(
            {"activation_map": m, "reachable": len(m)},
            ensure_ascii=False, indent=2,
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
