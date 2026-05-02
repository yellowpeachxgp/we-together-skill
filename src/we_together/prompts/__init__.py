"""Prompts 目录集中化：后续所有 LLM prompt 模板放这里。

当前已有的散在各 service 的 prompt 逐步迁移：
  - memory_condenser_service.py -> condense.txt
  - persona_drift_service.py -> persona_drift.txt
  - llm_extraction_service.py -> extract_candidates.txt
  - event_causality_service.py -> causality.txt
  - what_if_service.py -> what_if.txt
  - eval/llm_judge.py -> judge_fidelity.txt

迁移节奏：每次改动某 service 时顺手把它的 prompt 抽到这里。
现在只提供 load_prompt(name) 入口。
"""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent / "templates"


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def list_prompts() -> list[str]:
    if not PROMPTS_DIR.exists():
        return []
    return sorted(p.stem for p in PROMPTS_DIR.glob("*.txt"))
