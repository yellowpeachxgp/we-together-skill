"""Coze/Dify adapter：把 we-together 暴露为 plugin schema。

Coze Plugin 的 OpenAPI schema 是 JSON 形式。这里只提供最小转换函数：
  - build_plugin_schema() → OpenAPI 0.1 风格的 dict
  - parse_plugin_invocation(raw) → SkillRequest

保持纯函数，无外部依赖。
"""
from __future__ import annotations

from we_together.runtime.skill_runtime import SkillRequest


def build_plugin_schema() -> dict:
    return {
        "schema_version": "v1",
        "plugin_name": "we_together",
        "description": "Scene-aware social graph skill",
        "actions": [
            {
                "name": "run_turn",
                "description": "Run a scene-aware conversation turn",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scene_id": {"type": "string"},
                        "input": {"type": "string"},
                    },
                    "required": ["scene_id", "input"],
                },
            }
        ],
    }


def parse_plugin_invocation(raw: dict) -> SkillRequest:
    action = raw.get("action", "")
    params = raw.get("parameters", {}) or {}
    if action != "run_turn":
        raise ValueError(f"unknown action: {action}")
    return SkillRequest(
        system_prompt="you are we-together plugin",
        messages=[{"role": "user", "content": params.get("input", "")}],
        retrieval_package={},
        scene_id=params.get("scene_id", ""),
        user_input=params.get("input", ""),
        metadata={"adapter": "coze", "raw_action": action},
    )
