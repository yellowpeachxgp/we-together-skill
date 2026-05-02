"""Baseline + 回归检测。"""
from __future__ import annotations

import json
from pathlib import Path

from we_together.errors import ConfigError

DEFAULT_REGRESSION_TOLERANCE = 0.05


def save_baseline(metrics: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2))


def load_baseline(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"baseline not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def detect_regression(
    current: dict, baseline: dict, *, tolerance: float = DEFAULT_REGRESSION_TOLERANCE,
) -> dict:
    regressions: list[dict] = []
    for key in ("precision", "recall", "f1"):
        b = float(baseline.get(key, 0.0))
        c = float(current.get(key, 0.0))
        if b > 0 and (b - c) > tolerance:
            regressions.append({
                "metric": key,
                "baseline": b,
                "current": c,
                "delta": round(c - b, 4),
            })
    return {
        "passed": len(regressions) == 0,
        "tolerance": tolerance,
        "regressions": regressions,
    }
