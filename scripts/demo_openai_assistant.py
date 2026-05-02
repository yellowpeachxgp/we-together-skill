"""scripts/demo_openai_assistant.py — demo：把 we-together Skill 以 OpenAI Assistants tools 调用。

Mock 模式：不真连 OpenAI，只展示 tool_list + 一次 run_turn 的 payload 形状。
真跑模式：`WE_TOGETHER_LLM_PROVIDER=openai_compat` 且配好 key，才会真调。

用法:
  python scripts/demo_openai_assistant.py --root .
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.runtime.adapters.mcp_adapter import build_mcp_tools
from we_together.runtime.adapters.openai_adapter import OpenAISkillAdapter
from we_together.runtime.skill_runtime import SkillRequest


def mcp_tools_to_openai_function_schema(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object"}),
            },
        }
        for t in tools
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    _ = Path(args.root).resolve()

    tools = build_mcp_tools()
    oa_tools = mcp_tools_to_openai_function_schema(tools)

    req = SkillRequest(
        system_prompt="You are a we-together agent.",
        messages=[{"role": "user", "content": "summarize the graph"}],
        retrieval_package={}, scene_id="demo", user_input="summarize the graph",
        tools=[{"name": t["name"], "description": t.get("description", ""),
                "input_schema": t.get("inputSchema", {})} for t in tools],
    )
    adapter = OpenAISkillAdapter()
    payload = adapter.build_payload(req)

    out = {
        "skill_schema_version": req.schema_version,
        "openai_assistant_tools": oa_tools,
        "adapter_payload": {
            "messages": payload["messages"],
            "tool_count": len(payload.get("tools", [])),
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
