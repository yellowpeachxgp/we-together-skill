"""scripts/world_cli.py — CLI: 世界对象 CRUD。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services import world_service as ws
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_obj = sub.add_parser("register-object")
    ap_obj.add_argument("--root", default=".")
    ap_obj.add_argument("--tenant-id", default=None)
    ap_obj.add_argument("--kind", required=True)
    ap_obj.add_argument("--name")
    ap_obj.add_argument("--owner-id")
    ap_obj.add_argument("--owner-type", default="person")

    ap_place = sub.add_parser("register-place")
    ap_place.add_argument("--root", default=".")
    ap_place.add_argument("--tenant-id", default=None)
    ap_place.add_argument("--name", required=True)
    ap_place.add_argument("--scope")
    ap_place.add_argument("--parent")

    ap_proj = sub.add_parser("register-project")
    ap_proj.add_argument("--root", default=".")
    ap_proj.add_argument("--tenant-id", default=None)
    ap_proj.add_argument("--name", required=True)
    ap_proj.add_argument("--goal")
    ap_proj.add_argument("--participants", nargs="*")

    ap_w = sub.add_parser("active-world")
    ap_w.add_argument("--root", default=".")
    ap_w.add_argument("--tenant-id", default=None)
    ap_w.add_argument("--scene", required=True)

    args = ap.parse_args()
    tenant_root = resolve_tenant_root(Path(args.root).resolve(), getattr(args, "tenant_id", None))
    db = tenant_root / "db" / "main.sqlite3"

    if args.cmd == "register-object":
        r = ws.register_object(db, kind=args.kind, name=args.name,
                                owner_type=args.owner_type, owner_id=args.owner_id)
    elif args.cmd == "register-place":
        r = ws.register_place(db, name=args.name, scope=args.scope,
                                parent_place_id=args.parent)
    elif args.cmd == "register-project":
        r = ws.register_project(db, name=args.name, goal=args.goal,
                                 participants=args.participants or [])
    elif args.cmd == "active-world":
        r = ws.active_world_for_scene(db, args.scene)
    else:
        r = {"error": "unknown"}

    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
