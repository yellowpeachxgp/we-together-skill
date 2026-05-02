"""Agent loop：让 chat 支持 tool_call → tool_result 循环。

简化实现：
  - run_turn_agent(scene_id, user_input, *, tool_dispatcher, llm_client, max_iters=3)
  - 使用 llm_client.chat_json 驱动：LLM 返回
      {"action": "tool_call", "tool": "name", "args": {...}}  -> 调 dispatcher, 继续
      {"action": "respond", "text": "..."}                    -> 结束
  - 每一步记录为 dialogue_event（event_type='tool_use_event' 或 'dialogue_event'）

这不是生产级 agent，是最小可用链，给 Phase 9 的宿主适配打基础。
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from we_together.db.connection import connect
from we_together.llm.client import LLMClient, LLMMessage


@dataclass
class AgentStep:
    step_type: str  # 'tool_call' | 'tool_result' | 'respond'
    tool: str | None
    args: dict | None
    result: str | None
    text: str | None


@dataclass
class AgentRunResult:
    final_text: str
    steps: list[AgentStep]
    event_ids: list[str]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _log_event(db_path: Path, scene_id: str, event_type: str, summary: str) -> str:
    import uuid
    eid = f"evt_{event_type}_{uuid.uuid4().hex[:10]}"
    conn = connect(db_path)
    conn.execute(
        """INSERT INTO events(event_id, event_type, source_type, scene_id, timestamp,
           summary, visibility_level, confidence, is_structured,
           raw_evidence_refs_json, metadata_json, created_at)
           VALUES(?, ?, 'agent_loop', ?, ?, ?, 'visible', 0.7, 1, '[]', '{}', ?)""",
        (eid, event_type, scene_id, _now(), summary, _now()),
    )
    conn.commit()
    conn.close()
    return eid


def run_turn_agent(
    db_path: Path,
    *,
    scene_id: str,
    user_input: str,
    tool_dispatcher: dict[str, Callable[[dict], str]],
    llm_client: LLMClient,
    max_iters: int = 3,
) -> AgentRunResult:
    """最小 agent loop。LLM 通过 chat_json 返回 action 指令，本函数分发。"""
    messages: list[LLMMessage] = [
        LLMMessage(role="system", content="你是 we-together 代理。可选工具: " + ", ".join(tool_dispatcher)),
        LLMMessage(role="user", content=user_input),
    ]
    steps: list[AgentStep] = []
    events: list[str] = []

    for _ in range(max_iters):
        try:
            payload = llm_client.chat_json(
                messages,
                schema_hint={"action": "tool_call|respond", "tool": "str?",
                             "args": "obj?", "text": "str?"},
            )
        except Exception as exc:
            final = f"[agent error] {exc}"
            steps.append(AgentStep(step_type="respond", tool=None, args=None,
                                    result=None, text=final))
            return AgentRunResult(final_text=final, steps=steps, event_ids=events)

        action = payload.get("action", "respond")
        if action == "tool_call":
            tool = str(payload.get("tool", ""))
            args = payload.get("args") or {}
            steps.append(AgentStep(step_type="tool_call", tool=tool, args=args,
                                    result=None, text=None))
            events.append(_log_event(db_path, scene_id, "tool_use_event",
                                     f"call {tool} args={args}"))
            if tool not in tool_dispatcher:
                result = f"[unknown tool {tool}]"
            else:
                try:
                    result = tool_dispatcher[tool](args)
                except Exception as exc:
                    result = f"[tool error] {exc}"
            steps.append(AgentStep(step_type="tool_result", tool=tool, args=None,
                                    result=result, text=None))
            events.append(_log_event(db_path, scene_id, "tool_result_event",
                                     f"result {tool} = {result[:80]}"))
            messages.append(LLMMessage(role="assistant", content=f"tool_call {tool}"))
            messages.append(LLMMessage(role="user", content=f"tool_result: {result}"))
            continue

        text = str(payload.get("text", "") or "").strip()
        steps.append(AgentStep(step_type="respond", tool=None, args=None, result=None,
                                text=text))
        events.append(_log_event(db_path, scene_id, "dialogue_event",
                                 f"agent: {text[:80]}"))
        return AgentRunResult(final_text=text, steps=steps, event_ids=events)

    final = "[agent exhausted max_iters]"
    steps.append(AgentStep(step_type="respond", tool=None, args=None, result=None,
                            text=final))
    return AgentRunResult(final_text=final, steps=steps, event_ids=events)
