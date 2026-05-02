"""scripts/plugins_list.py — 打印已发现的 plugin 状态。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.plugins import plugin_registry as pr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reload", action="store_true",
                    help="force rediscover entry_points")
    args = ap.parse_args()

    result = pr.discover(reload=args.reload)
    st = pr.status()
    print(json.dumps({
        "discover": result,
        "status": st,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
