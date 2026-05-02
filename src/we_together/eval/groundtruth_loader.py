"""Groundtruth 数据加载器 + schema 校验。

schema 约定:
  {
    "benchmark_name": str,
    "persons": [{"person_id": str, "primary_name": str}],
    "expected_relations": [
        {"person_a": str, "person_b": str, "core_type": str, "min_strength": float}
    ],
    "expected_scenes": [{"scene_type": str, "participant_names": [str, ...]}]
  }
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from we_together.errors import ConfigError


@dataclass
class GroundtruthSet:
    benchmark_name: str
    persons: list[dict] = field(default_factory=list)
    expected_relations: list[dict] = field(default_factory=list)
    expected_scenes: list[dict] = field(default_factory=list)

    def relation_pairs(self) -> set[tuple[str, str, str]]:
        """规范化的 (a_name, b_name, core_type) 集合（a<=b 排序后）。"""
        out: set[tuple[str, str, str]] = set()
        for r in self.expected_relations:
            a, b = sorted([r["person_a"], r["person_b"]])
            out.add((a, b, r["core_type"]))
        return out


def load_groundtruth(path: Path) -> GroundtruthSet:
    if not path.exists():
        raise ConfigError(f"groundtruth not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("benchmark_name", "persons"):
        if key not in data:
            raise ConfigError(f"groundtruth missing field: {key}")
    return GroundtruthSet(
        benchmark_name=data["benchmark_name"],
        persons=list(data.get("persons", [])),
        expected_relations=list(data.get("expected_relations", [])),
        expected_scenes=list(data.get("expected_scenes", [])),
    )
