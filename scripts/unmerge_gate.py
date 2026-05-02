"""为 merged person 打开 operator-gated unmerge branch。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.services.tenant_router import resolve_tenant_root
from we_together.services.unmerge_gate_service import (
    open_unmerge_branch_for_merged_person,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="为 merged person 打开 operator-gated unmerge branch")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--source-person-id", required=True)
    ap.add_argument("--confidence", type=float, default=0.8)
    ap.add_argument("--reason", default="contradiction-derived operator gate")
    ap.add_argument("--note", default=None)
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root), args.tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    if not db_path.exists():
        print(json.dumps({"error": "db not found"}))
        return 1

    try:
        result = open_unmerge_branch_for_merged_person(
            db_path,
            source_pid=args.source_person_id,
            confidence=args.confidence,
            reason=args.reason,
            note=args.note,
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
