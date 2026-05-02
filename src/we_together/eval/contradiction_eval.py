"""Contradiction eval：对 benchmarks/contradiction_groundtruth.json 跑 judge_contradiction。"""
from __future__ import annotations

import json
from pathlib import Path

from we_together.services.contradiction_detector import judge_contradiction


def run_contradiction_eval(benchmark_path: Path, *, llm_client) -> dict:
    data = json.loads(benchmark_path.read_text(encoding="utf-8"))
    results: list[dict] = []
    tp = fp = tn = fn = 0
    for pair in data.get("pairs", []):
        judged = judge_contradiction(pair["a"], pair["b"], llm_client=llm_client)
        predicted = judged["is_contradiction"]
        expected = pair["is_contradiction"]
        if predicted and expected:
            tp += 1
        elif predicted and not expected:
            fp += 1
        elif not predicted and not expected:
            tn += 1
        else:
            fn += 1
        results.append({
            "a": pair["a"][:40], "b": pair["b"][:40],
            "expected": expected, "predicted": predicted,
            "confidence": judged["confidence"],
        })
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    return {
        "benchmark": data.get("benchmark_name"),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "results": results,
    }
