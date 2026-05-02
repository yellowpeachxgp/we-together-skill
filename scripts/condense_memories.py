"""记忆凝练 CLI：把同主题多条 memory 压成 1 条 condensed_memory。

用法:
  .venv/bin/python scripts/condense_memories.py --root . [--max-clusters 20]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.memory_condenser_service import condense_memory_clusters
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="db-backed project root")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--max-clusters", type=int, default=20)
    ap.add_argument("--min-cluster-size", type=int, default=2)
    args = ap.parse_args()

    project_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db_path = project_root / "db" / "main.sqlite3"
    if not db_path.exists():
        print(f"db not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    result = condense_memory_clusters(
        db_path=db_path,
        max_clusters=args.max_clusters,
        min_cluster_size=args.min_cluster_size,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
