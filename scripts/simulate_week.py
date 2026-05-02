"""scripts/simulate_week.py — 跑 N 天 tick 并输出 + 归档报告。

用法:
  python scripts/simulate_week.py --root . --ticks 7 --budget 30 [--archive]

输出: JSON 报告含每 tick 的 decay/drift/proactive 统计 + 合理性评估
若 --archive，同时写 benchmarks/tick_runs/<ISO timestamp>.json（可 reprod）
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.llm import get_llm_client
from we_together.services.tenant_router import resolve_tenant_root
from we_together.services.tick_sanity import evaluate
from we_together.services.time_simulator import TickBudget, simulate


def build_report(db: Path, *, ticks: int, budget: int,
                  self_activation: bool = False) -> dict:
    b = TickBudget(llm_calls=budget)
    sim = simulate(
        db, ticks=ticks, budget=b,
        llm_client=get_llm_client(),
        do_self_activation=self_activation,
    )
    sim["sanity"] = evaluate(db, ticks=ticks)
    sim["meta"] = {
        "ticks": ticks,
        "budget_input": budget,
        "budget_remaining": b.llm_calls,
        "self_activation": self_activation,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    return sim


def archive(report: dict, bench_dir: Path) -> Path:
    bench_dir.mkdir(parents=True, exist_ok=True)
    name = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ") + ".json"
    path = bench_dir / name
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--ticks", type=int, default=7)
    ap.add_argument("--budget", type=int, default=30,
                    help="total LLM calls across all ticks")
    ap.add_argument("--self-activation", action="store_true")
    ap.add_argument("--archive", action="store_true",
                    help="write report to benchmarks/tick_runs/<ts>.json")
    args = ap.parse_args()

    root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = root / "db" / "main.sqlite3"
    if not db.exists():
        print(json.dumps({"error": "db not found", "path": str(db)}))
        return 1

    report = build_report(
        db, ticks=args.ticks, budget=args.budget,
        self_activation=args.self_activation,
    )

    if args.archive:
        bench_dir = root / "benchmarks" / "tick_runs"
        path = archive(report, bench_dir)
        report["archived_to"] = str(path.relative_to(root))

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
