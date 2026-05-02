"""Persona drift eval：给定事件序列 + 期望画像，走 llm_judge 打分。"""
from __future__ import annotations

import json
from pathlib import Path

from we_together.eval.llm_judge import judge_fidelity


def run_persona_drift_eval(
    benchmark_path: Path, *, generated_persona_by_case: dict[str, str], llm_client,
) -> dict:
    data = json.loads(benchmark_path.read_text(encoding="utf-8"))
    results: list[dict] = []
    passed = 0
    for case in data.get("cases", []):
        case_id = case["case_id"]
        generated = generated_persona_by_case.get(case_id, "")
        if not generated:
            continue
        # 用 LLM judge：把 case["events"] 作为 sources，generated 作为 summary
        judged = judge_fidelity(case["events"], generated, llm_client=llm_client)
        ok = judged["fidelity_score"] >= case.get("expected_fidelity_min", 0.5)
        if ok:
            passed += 1
        results.append({
            "case_id": case_id,
            "generated": generated,
            "expected_persona": case["expected_persona"],
            "fidelity_score": judged["fidelity_score"],
            "expected_min": case.get("expected_fidelity_min", 0.5),
            "passed": ok,
        })
    total = len(results)
    return {
        "benchmark": data.get("benchmark_name"),
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "cases": results,
    }
