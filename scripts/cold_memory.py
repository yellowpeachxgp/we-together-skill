"""冷记忆归档 CLI：archive / list / restore。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.memory_archive_service import (
    archive_cold_memories,
    list_cold_memories,
    restore_cold_memory,
)
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="db-backed project root")
    ap.add_argument("--tenant-id", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_arch = sub.add_parser("archive")
    p_arch.add_argument("--window-days", type=int, default=180)
    p_arch.add_argument("--relevance-threshold", type=float, default=0.15)

    sub.add_parser("list")

    p_rest = sub.add_parser("restore")
    p_rest.add_argument("memory_id")

    args = ap.parse_args()
    project_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db_path = project_root / "db" / "main.sqlite3"
    if not db_path.exists():
        print(f"db not found: {db_path}", file=sys.stderr)
        sys.exit(2)

    if args.cmd == "archive":
        r = archive_cold_memories(db_path, window_days=args.window_days,
                                  relevance_threshold=args.relevance_threshold)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    elif args.cmd == "list":
        print(json.dumps(list_cold_memories(db_path), ensure_ascii=False, indent=2))
    elif args.cmd == "restore":
        ok = restore_cold_memory(db_path, args.memory_id)
        print(json.dumps({"restored": ok, "memory_id": args.memory_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
