"""多场景并发激活：同时对多个 active scene 构建 retrieval，并把 activation_map 聚合。

合并规则：
  - 同 person_id 去重
  - activation_state 取 priority 更高者（explicit > latent 等）
  - activation_score 取 max

输出：
  {
    "scene_ids": [...],
    "activation_map": [{person_id, activation_score, activation_state, source_scenes}],
    "per_scene": {scene_id: retrieval_package},
  }
"""
from __future__ import annotations

from pathlib import Path

from we_together.runtime.sqlite_retrieval import (
    STATE_PRIORITY,
    build_runtime_retrieval_package_from_db,
)


def _merge_activation_entry(
    merged: dict[str, dict],
    entry: dict,
    scene_id: str,
) -> None:
    existing = merged.get(entry["person_id"])
    if existing is None:
        merged[entry["person_id"]] = {
            "person_id": entry["person_id"],
            "activation_score": entry["activation_score"],
            "activation_state": entry["activation_state"],
            "activation_reason_summary": entry.get("activation_reason_summary", ""),
            "source_scenes": [scene_id],
        }
        return

    if scene_id not in existing["source_scenes"]:
        existing["source_scenes"].append(scene_id)

    if STATE_PRIORITY[entry["activation_state"]] > STATE_PRIORITY[existing["activation_state"]]:
        existing["activation_state"] = entry["activation_state"]
        existing["activation_reason_summary"] = entry.get(
            "activation_reason_summary", existing["activation_reason_summary"]
        )

    if entry["activation_score"] > existing["activation_score"]:
        existing["activation_score"] = entry["activation_score"]


def build_multi_scene_activation(
    db_path: Path,
    scene_ids: list[str],
    *,
    max_memories: int | None = 20,
    max_relations: int | None = 10,
    max_states: int | None = 30,
    max_recent_changes: int | None = 5,
) -> dict:
    if not scene_ids:
        return {"scene_ids": [], "activation_map": [], "per_scene": {}}

    per_scene: dict[str, dict] = {}
    merged: dict[str, dict] = {}

    for scene_id in scene_ids:
        pkg = build_runtime_retrieval_package_from_db(
            db_path=db_path,
            scene_id=scene_id,
            max_memories=max_memories,
            max_relations=max_relations,
            max_states=max_states,
            max_recent_changes=max_recent_changes,
        )
        per_scene[scene_id] = pkg
        for entry in pkg.get("activation_map", []):
            _merge_activation_entry(merged, entry, scene_id)

    activation_map = sorted(
        merged.values(),
        key=lambda x: (x["activation_score"], x["person_id"]),
        reverse=True,
    )

    return {
        "scene_ids": list(scene_ids),
        "activation_map": activation_map,
        "per_scene": per_scene,
    }
