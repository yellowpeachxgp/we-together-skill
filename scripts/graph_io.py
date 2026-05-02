"""Graph canonical I/O CLI：export / import 子命令。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services.graph_serializer import (
    dump_graph_to_file,
    load_graph_from_file,
)
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("export")
    p1.add_argument("--root", default=".")
    p1.add_argument("--tenant-id", default=None)
    p1.add_argument("--out", required=True)

    p2 = sub.add_parser("import")
    p2.add_argument("--input", required=True)
    p2.add_argument("--target", required=True)
    p2.add_argument("--tenant-id", default=None)

    args = ap.parse_args()
    if args.cmd == "export":
        tenant_root = resolve_tenant_root(Path(args.root).resolve(), getattr(args, "tenant_id", None))
        db = tenant_root / "db" / "main.sqlite3"
        r = dump_graph_to_file(db, Path(args.out).resolve())
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        target_root = resolve_tenant_root(Path(args.target).resolve(), getattr(args, "tenant_id", None))
        r = load_graph_from_file(Path(args.input).resolve(), target_root)
        print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
