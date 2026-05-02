"""LangChain adapter：把 we-together 暴露为 LangChain Tool 可调用的函数。

接口设计（不 import langchain 以免硬依赖）:
  - class WeTogetherLCTool:
      name = "we_together_chat"
      description = "Run a scene-aware turn and return the final text."
      def run(self, payload: {"scene_id": str, "input": str}) -> str

同样提供裸函数 invoke_as_lc_tool(payload, run_turn_fn) 方便测试。
"""
from __future__ import annotations

from typing import Callable


def invoke_as_lc_tool(
    payload: dict, *, run_turn_fn: Callable[[str, str], str],
) -> str:
    scene_id = payload.get("scene_id") or payload.get("scene")
    text = payload.get("input") or payload.get("text") or ""
    if not scene_id:
        raise ValueError("scene_id is required")
    return run_turn_fn(scene_id, text)


class WeTogetherLCTool:
    name = "we_together_chat"
    description = "Run a scene-aware turn and return the final text."

    def __init__(self, run_turn_fn: Callable[[str, str], str]):
        self._run_turn_fn = run_turn_fn

    def run(self, payload: dict) -> str:
        return invoke_as_lc_tool(payload, run_turn_fn=self._run_turn_fn)
