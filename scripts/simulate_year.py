"""scripts/simulate_year.py — 365 tick 加速模拟一年。

用法:
  python scripts/simulate_year.py --root . --days 365 --budget 50 --archive-monthly

每 tick 前 advance graph_clock 1 天；结束后跑 integrity_audit + sanity 评估。
--archive-monthly：按 30 天切片聚合月度，整份报告归档到 benchmarks/year_runs/
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.llm import get_llm_client
from we_together.llm.audited_client import UsageAuditedLLMClient, estimate_cost_usd
from we_together.services import graph_clock
from we_together.services.integrity_audit import full_audit
from we_together.services.tenant_router import resolve_tenant_root
from we_together.services.tick_sanity import evaluate
from we_together.services.time_simulator import TickBudget, simulate


def _month_index(day: int) -> int:
    return day // 30


def _empty_usage_summary() -> dict:
    return {
        "total_calls": 0,
        "total_tokens": 0,
        "by_provider": {},
    }


def _clone_usage_summary(summary: dict) -> dict:
    return json.loads(json.dumps(summary))


def _usage_delta(before: dict, after: dict) -> dict:
    out = _empty_usage_summary()
    providers = set(before.get("by_provider", {})) | set(after.get("by_provider", {}))
    for provider in providers:
        b = before.get("by_provider", {}).get(provider, {})
        a = after.get("by_provider", {}).get(provider, {})
        calls = int(a.get("calls", 0)) - int(b.get("calls", 0))
        prompt = int(a.get("prompt_tokens", 0)) - int(b.get("prompt_tokens", 0))
        completion = int(a.get("completion_tokens", 0)) - int(b.get("completion_tokens", 0))
        if calls or prompt or completion:
            out["by_provider"][provider] = {
                "calls": calls,
                "prompt_tokens": prompt,
                "completion_tokens": completion,
            }
            out["total_calls"] += calls
            out["total_tokens"] += prompt + completion
    return out


def _merge_usage_summary(base: dict, delta: dict) -> dict:
    merged = _clone_usage_summary(base)
    merged["total_calls"] += int(delta.get("total_calls", 0))
    merged["total_tokens"] += int(delta.get("total_tokens", 0))
    for provider, values in delta.get("by_provider", {}).items():
        bucket = merged["by_provider"].setdefault(
            provider,
            {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0},
        )
        bucket["calls"] += int(values.get("calls", 0))
        bucket["prompt_tokens"] += int(values.get("prompt_tokens", 0))
        bucket["completion_tokens"] += int(values.get("completion_tokens", 0))
    return merged


def archive_monthly_reports(monthly: list[dict], report_dir: Path) -> list[str]:
    report_dir.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for item in monthly:
        path = report_dir / f"year_month_{int(item['month']):02d}.json"
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.append(str(path))
    return paths


def run_year(
    db: Path, *,
    days: int, budget: int,
    do_self_activation: bool = False,
    archive_dir: Path | None = None,
    monthly_report_dir: Path | None = None,
    provider: str | None = None,
    llm_client=None,
    prompt_price_per_1k: float = 0.0,
    completion_price_per_1k: float = 0.0,
) -> dict:
    b = TickBudget(llm_calls=budget)
    monthly: dict[int, dict] = {}
    audited_client = None
    if llm_client is not None:
        audited_client = UsageAuditedLLMClient(llm_client)
    elif budget > 0 or do_self_activation or provider:
        audited_client = UsageAuditedLLMClient(get_llm_client(provider))
    previous_usage = _empty_usage_summary()

    for day in range(days):
        try:
            graph_clock.advance(db, days=1)
        except Exception:
            pass
        r = simulate(
            db,
            ticks=1,
            budget=b,
            llm_client=audited_client,
            do_self_activation=do_self_activation,
        )
        month = _month_index(day)
        mon = monthly.setdefault(
            month,
            {
                "month": month,
                "days": 0,
                "snapshots_added": 0,
                "llm_usage": _empty_usage_summary(),
                "estimated_cost_usd": 0.0,
            },
        )
        mon["days"] += 1
        mon["snapshots_added"] += len([s for s in r["snapshot_ids"] if s])
        current_usage = (
            audited_client.summary()
            if audited_client is not None
            else _empty_usage_summary()
        )
        delta = _usage_delta(previous_usage, current_usage)
        mon["llm_usage"] = _merge_usage_summary(mon["llm_usage"], delta)
        mon["estimated_cost_usd"] = estimate_cost_usd(
            mon["llm_usage"],
            prompt_price_per_1k=prompt_price_per_1k,
            completion_price_per_1k=completion_price_per_1k,
        )
        previous_usage = _clone_usage_summary(current_usage)

    sanity = evaluate(db, ticks=days)
    integrity = full_audit(db)
    llm_usage = audited_client.summary() if audited_client is not None else {
        "total_calls": 0,
        "total_tokens": 0,
        "by_provider": {},
    }

    final_report = {
        "days": days, "budget_input": budget,
        "budget_remaining": b.llm_calls,
        "total_snapshots_added": sum(m["snapshots_added"] for m in monthly.values()),
        "total_months": len(monthly),
        "monthly": sorted(monthly.values(), key=lambda x: x["month"]),
        "sanity": sanity,
        "integrity": {
            "total_issues": integrity["total_issues"],
            "healthy": integrity["healthy"],
        },
        "llm_provider": audited_client.provider if audited_client is not None else None,
        "llm_usage": llm_usage,
        "estimated_cost_usd": estimate_cost_usd(
            llm_usage,
            prompt_price_per_1k=prompt_price_per_1k,
            completion_price_per_1k=completion_price_per_1k,
        ),
        "generated_at": datetime.now(UTC).isoformat(),
    }

    if archive_dir is not None:
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
        path = archive_dir / f"year_run_{ts}.json"
        path.write_text(
            json.dumps(final_report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        final_report["archived_to"] = str(path)

    if monthly_report_dir is not None:
        paths = archive_monthly_reports(final_report["monthly"], monthly_report_dir)
        final_report["monthly_report_dir"] = str(monthly_report_dir)
        final_report["monthly_reports"] = paths

    return final_report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--budget", type=int, default=50)
    ap.add_argument("--provider", default=None)
    ap.add_argument("--self-activation", action="store_true")
    ap.add_argument("--archive-monthly", action="store_true")
    ap.add_argument("--monthly-report-dir", default=None)
    ap.add_argument("--dry-run-provider-check", action="store_true")
    ap.add_argument("--prompt-price-per-1k", type=float, default=0.0)
    ap.add_argument("--completion-price-per-1k", type=float, default=0.0)
    args = ap.parse_args()

    if args.dry_run_provider_check:
        try:
            client = get_llm_client(args.provider)
        except Exception as exc:
            print(json.dumps({"ready": False, "error": str(exc)}))
            return 2
        print(
            json.dumps(
                {
                    "ready": True,
                    "provider": client.provider,
                    "model": getattr(client, "model", None),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = root / "db" / "main.sqlite3"
    if not db.exists():
        print(json.dumps({"error": "db not found"}))
        return 1

    archive_dir = None
    if args.archive_monthly:
        archive_dir = root / "benchmarks" / "year_runs"
    monthly_report_dir = Path(args.monthly_report_dir).resolve() if args.monthly_report_dir else None
    if args.archive_monthly and monthly_report_dir is None:
        monthly_report_dir = root / "benchmarks" / "year_runs" / "monthly"

    report = run_year(
        db, days=args.days, budget=args.budget,
        do_self_activation=args.self_activation,
        archive_dir=archive_dir,
        monthly_report_dir=monthly_report_dir,
        provider=args.provider,
        prompt_price_per_1k=args.prompt_price_per_1k,
        completion_price_per_1k=args.completion_price_per_1k,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
