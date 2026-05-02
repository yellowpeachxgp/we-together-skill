"""Relation timeline CLI：打印 relation 的 strength 时序。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.relation_history_service import (
    get_relation_strength_series,
    list_relations_with_changes,
)
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--relation-id", default=None)
    ap.add_argument("--bucket", choices=["day", "week", "month"], default="week")
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    if args.relation_id:
        series = get_relation_strength_series(db, args.relation_id, bucket=args.bucket)
        print(json.dumps({
            "relation_id": args.relation_id, "bucket": args.bucket,
            "series": series,
        }, ensure_ascii=False, indent=2))
    else:
        top = list_relations_with_changes(db, limit=args.top)
        print(json.dumps({"top_relations_by_changes": top}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
