import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.snapshot_service import list_snapshots, replay_patches_after_snapshot, rollback_to_snapshot
from we_together.services.tenant_router import resolve_tenant_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List or rollback snapshots")
    parser.add_argument("--root", default=str(ROOT), help="Project root")
    parser.add_argument("--tenant-id", default=None)
    sub = parser.add_subparsers(dest="command")

    list_parser = sub.add_parser("list", help="List all snapshots")
    list_parser.add_argument("--root", default=argparse.SUPPRESS, help="Project root")
    list_parser.add_argument("--tenant-id", default=argparse.SUPPRESS)

    rb = sub.add_parser("rollback", help="Rollback to a snapshot")
    rb.add_argument("--snapshot-id", required=True)
    rb.add_argument("--root", default=argparse.SUPPRESS, help="Project root")
    rb.add_argument("--tenant-id", default=argparse.SUPPRESS)

    rp = sub.add_parser("replay", help="Replay rolled-back patches after a snapshot")
    rp.add_argument("--snapshot-id", required=True)
    rp.add_argument("--root", default=argparse.SUPPRESS, help="Project root")
    rp.add_argument("--tenant-id", default=argparse.SUPPRESS)

    args = parser.parse_args(argv)
    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"

    if args.command == "list":
        snapshots = list_snapshots(db_path)
        print(json.dumps(snapshots, ensure_ascii=False, indent=2))
    elif args.command == "rollback":
        result = rollback_to_snapshot(db_path, args.snapshot_id)
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "replay":
        result = replay_patches_after_snapshot(db_path, args.snapshot_id)
        print(json.dumps(result, ensure_ascii=False))
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
