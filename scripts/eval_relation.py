"""scripts/eval_relation.py：跑 relation 推理 eval + 报告。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.eval.regression import detect_regression, load_baseline, save_baseline
from we_together.eval.relation_inference import evaluate_relation_inference
from we_together.services.tenant_router import resolve_tenant_root


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--benchmark", default="society_c")
    ap.add_argument("--baseline", type=Path, default=None,
                    help="baseline.json 用于回归比较")
    ap.add_argument("--save-baseline", type=Path, default=None,
                    help="保存当前结果为 baseline")
    args = ap.parse_args()

    project_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db_path = project_root / "db" / "main.sqlite3"
    gt_path = Path(__file__).resolve().parents[1] / "benchmarks" / \
        f"{args.benchmark}_groundtruth.json"

    result = evaluate_relation_inference(db_path=db_path, groundtruth_path=gt_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.save_baseline:
        save_baseline(result, args.save_baseline)
        print(f"\nbaseline saved → {args.save_baseline}")

    if args.baseline:
        try:
            baseline = load_baseline(args.baseline)
            reg = detect_regression(result, baseline)
            print("\nregression check:")
            print(json.dumps(reg, ensure_ascii=False, indent=2))
            if not reg["passed"]:
                return 3
        except Exception as exc:
            print(f"regression check failed: {exc}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
