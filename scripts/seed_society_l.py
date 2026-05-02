"""scripts/seed_society_l.py — 合成 500 人大社会（使用 m 的 seed 逻辑 + 放大）。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from seed_society_m import seed

from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--n", type=int, default=500)
    ap.add_argument("--seed-value", type=int, default=2026)
    args = ap.parse_args()
    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    r = seed(tenant_root, n=args.n, seed_value=args.seed_value)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
