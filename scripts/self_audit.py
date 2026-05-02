"""scripts/self_audit.py — 综合自审。

用法:
  python scripts/self_audit.py              # 完整自描述
  python scripts/self_audit.py --adrs       # 只列 ADR
  python scripts/self_audit.py --invariants # 只列不变式
  python scripts/self_audit.py --services   # 只列 service
  python scripts/self_audit.py --migrations # 只列 migration
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.services import self_introspection as si


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adrs", action="store_true")
    ap.add_argument("--invariants", action="store_true")
    ap.add_argument("--services", action="store_true")
    ap.add_argument("--migrations", action="store_true")
    ap.add_argument("--plugins", action="store_true")
    ap.add_argument("--scripts", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    args = ap.parse_args()

    if args.adrs:
        print(json.dumps(si.list_adrs(), ensure_ascii=False, indent=2))
    elif args.invariants:
        print(json.dumps(si.list_invariants(), ensure_ascii=False, indent=2))
    elif args.services:
        print(json.dumps(si.list_services(), ensure_ascii=False, indent=2))
    elif args.migrations:
        print(json.dumps(si.list_migrations(), ensure_ascii=False, indent=2))
    elif args.plugins:
        print(json.dumps(si.list_plugins(), ensure_ascii=False, indent=2))
    elif args.scripts:
        print(json.dumps(si.list_scripts(), ensure_ascii=False, indent=2))
    elif args.coverage:
        print(json.dumps(si.invariant_coverage(), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(si.self_describe(), ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
