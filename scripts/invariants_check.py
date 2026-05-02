"""scripts/invariants_check.py — CLI 查看不变式覆盖。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.invariants import coverage_summary, get_invariant, list_as_dicts


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    ap_sum = sub.add_parser("summary")
    ap_sum.add_argument("--uncovered-only", action="store_true")

    ap_one = sub.add_parser("show")
    ap_one.add_argument("invariant_id", type=int)

    ap_list = sub.add_parser("list")

    args = ap.parse_args()

    if args.cmd == "summary":
        s = coverage_summary()
        if args.uncovered_only and not s["uncovered_ids"]:
            print(json.dumps({"ok": True, "uncovered": []}))
            return 0
        print(json.dumps(s, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "show":
        inv = get_invariant(args.invariant_id)
        if inv is None:
            print(json.dumps({"error": "not found"}))
            return 1
        print(json.dumps(inv.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "list":
        print(json.dumps(list_as_dicts(), ensure_ascii=False, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
