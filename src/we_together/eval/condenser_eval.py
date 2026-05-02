"""Condenser eval：对 benchmarks/condense_groundtruth.json 每条 case 跑 llm_judge."""
from __future__ import annotations

import json
from pathlib import Path

from we_together.eval.llm_judge import judge_fidelity


def run_condense_eval(
    benchmark_path: Path, *, llm_client,
) -> dict:
    data = json.loads(benchmark_path.read_text(encoding="utf-8"))
    results: list[dict] = []
    passed = 0
    for case in data.get("cases", []):
        judged = judge_fidelity(case["sources"], case["condensed"],
                                  llm_client=llm_client)
        ok = judged["fidelity_score"] >= case.get("expected_fidelity_min", 0.5)
        if ok:
            passed += 1
        results.append({
            "case_id": case["case_id"],
            "fidelity_score": judged["fidelity_score"],
            "expected_min": case.get("expected_fidelity_min", 0.5),
            "passed": ok,
            "missing_points": judged.get("missing_points", []),
            "fabrications": judged.get("fabrications", []),
        })
    total = len(results)
    return {
        "benchmark": data.get("benchmark_name"),
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "cases": results,
    }
