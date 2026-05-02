"""scripts/analyze.py：图谱分析 CLI（中心度/群体密度/孤立识别）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.graph_analytics import (
    compute_degree_centrality,
    compute_group_density,
    full_report,
    identify_isolated_persons,
)
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--mode", choices=["degree", "density", "isolated", "all"],
                    default="all")
    ap.add_argument("--window-days", type=int, default=30)
    args = ap.parse_args()
    project_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = project_root / "db" / "main.sqlite3"

    if args.mode == "degree":
        r = compute_degree_centrality(db)
    elif args.mode == "density":
        r = compute_group_density(db)
    elif args.mode == "isolated":
        r = identify_isolated_persons(db, window_days=args.window_days)
    else:
        r = full_report(db, window_days=args.window_days)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
