"""Agent tool-use 运行器（真接 adapter）。

Phase 25 升级：
  - 优先走 adapter-native 协议（llm_client.chat_with_tools → 原生 tool_use）
  - fallback 到 chat_json 的 action 协议（MockLLMClient 旧测试路径）
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from we_together.db.connection import connect
from we_together.llm.client import LLMClient, LLMMessage
from we_together.runtime.skill_runtime import SkillRequest, SkillResponse


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _log_event(db_path: Path | None, scene_id: str, event_type: str, summary: str) -> str | None:
    if db_path is None:
        return None
    eid = f"evt_{event_type}_{uuid.uuid4().hex[:10]}"
    conn = connect(db_path)
    conn.execute(
        """INSERT INTO events(event_id, event_type, source_type, scene_id, timestamp,
           summary, visibility_level, confidence, is_structured,
           raw_evidence_refs_json, metadata_json, created_at)
           VALUES(?, ?, 'agent_runner', ?, ?, ?, 'visible', 0.7, 1, '[]', '{}', ?)""",
        (eid, event_type, scene_id, _now(), summary, _now()),
    )
    conn.commit()
    conn.close()
    return eid


@dataclass
class AgentRunResult:
    response: SkillResponse
    steps: list[dict]
    event_ids: list[str]


def _prefers_native(llm_client) -> bool:
    """True if llm_client 应走 chat_with_tools 原生协议。

    - 没有 chat_with_tools → False
    - MockLLMClient：仅在 _scripted_tool_uses 非空时 True（保持旧测试兼容）
    - 真 provider：True
    """
    if not hasattr(llm_client, "chat_with_tools"):
        return False
    # Mock 的旧测试兼容：只在 scripted 了 tool_uses 时走 native
    if hasattr(llm_client, "_scripted_tool_uses"):
        return bool(llm_client._scripted_tool_uses)
    return True


def run_tool_use_loop(
    request: SkillRequest,
    *,
    llm_client: LLMClient,
    tool_dispatcher: dict[str, Callable[[dict], str]],
    db_path: Path | None = None,
    max_iters: int = 3,
    adapter_name: str = "openai_compat",
) -> AgentRunResult:
    """Tool-use loop。优先 chat_with_tools（原生），fallback chat_json。"""
    messages: list[LLMMessage] = [LLMMessage(role="system", content=request.system_prompt)]
    for m in request.messages:
        messages.append(LLMMessage(role=m["role"], content=m["content"]))

    steps: list[dict] = []
    event_ids: list[str] = []
    use_native = _prefers_native(llm_client) and bool(request.tools)

    for _ in range(max_iters):
        if use_native:
            try:
                payload_native = llm_client.chat_with_tools(messages, request.tools)
            except Exception as exc:
                final = f"[agent error] {exc}"
                return AgentRunResult(
                    response=SkillResponse(text=final, raw={"adapter": adapter_name, "error": True}),
                    steps=steps + [{"type": "error", "text": final}],
                    event_ids=event_ids,
                )
            tool_uses = payload_native.get("tool_uses") or []
            if tool_uses:
                for tu in tool_uses:
                    name = tu.get("name", "")
                    args = tu.get("input") or {}
                    steps.append({"type": "tool_call", "tool": name, "args": args,
                                   "call_id": tu.get("id", "")})
                    eid = _log_event(db_path, request.scene_id, "tool_use_event",
                                      f"call {name} args={args}")
                    if eid: event_ids.append(eid)
                    if name not in tool_dispatcher:
                        result = f"[unknown tool {name}]"; is_error = True
                    else:
                        try:
                            result = tool_dispatcher[name](args); is_error = False
                        except Exception as exc:
                            result = f"[tool error] {exc}"; is_error = True
                    steps.append({"type": "tool_result", "tool": name,
                                   "result": result, "is_error": is_error})
                    eid2 = _log_event(db_path, request.scene_id, "tool_result_event",
                                       f"result {name}={result[:80]} err={is_error}")
                    if eid2: event_ids.append(eid2)
                    messages.append(LLMMessage(role="assistant",
                                                 content=f"tool_call {name}"))
                    messages.append(LLMMessage(role="user",
                                                 content=f"tool_result: {result}" +
                                                         (" [ERROR]" if is_error else "")))
                continue
            text = (payload_native.get("text") or "").strip()
            steps.append({"type": "respond", "text": text})
            policy = request.retrieval_package.get("response_policy", {})
            resp = SkillResponse(
                text=text,
                speaker_person_id=policy.get("primary_speaker"),
                supporting_speakers=list(policy.get("supporting_speakers", [])),
                raw={"adapter": adapter_name, "tool_use": True,
                      "step_count": len(steps), "native": True},
            )
            return AgentRunResult(response=resp, steps=steps, event_ids=event_ids)

        # fallback: 旧 chat_json action 协议
        try:
            payload = llm_client.chat_json(
                messages,
                schema_hint={"action": "tool_call|respond",
                              "tool": "str?", "args": "obj?", "text": "str?"},
            )
        except Exception as exc:
            final = f"[agent error] {exc}"
            return AgentRunResult(
                response=SkillResponse(text=final, raw={"adapter": adapter_name, "error": True}),
                steps=steps + [{"type": "error", "text": final}],
                event_ids=event_ids,
            )

        action = payload.get("action", "respond")
        if action == "tool_call":
            tool = str(payload.get("tool", ""))
            args = payload.get("args") or {}
            steps.append({"type": "tool_call", "tool": tool, "args": args})
            eid = _log_event(db_path, request.scene_id, "tool_use_event",
                              f"call {tool} args={args}")
            if eid: event_ids.append(eid)
            if tool not in tool_dispatcher:
                result = f"[unknown tool {tool}]"; is_error = True
            else:
                try:
                    result = tool_dispatcher[tool](args); is_error = False
                except Exception as exc:
                    result = f"[tool error] {exc}"; is_error = True
            steps.append({"type": "tool_result", "tool": tool, "result": result,
                           "is_error": is_error})
            eid2 = _log_event(db_path, request.scene_id, "tool_result_event",
                               f"result {tool}={result[:80]} err={is_error}")
            if eid2: event_ids.append(eid2)
            messages.append(LLMMessage(role="assistant", content=f"tool_call {tool}"))
            messages.append(LLMMessage(role="user",
                                         content=f"tool_result: {result}" +
                                                 (" [ERROR]" if is_error else "")))
            continue

        text = str(payload.get("text", "") or "").strip()
        steps.append({"type": "respond", "text": text})
        policy = request.retrieval_package.get("response_policy", {})
        resp = SkillResponse(
            text=text,
            speaker_person_id=policy.get("primary_speaker"),
            supporting_speakers=list(policy.get("supporting_speakers", [])),
            raw={"adapter": adapter_name, "tool_use": True, "step_count": len(steps)},
        )
        return AgentRunResult(response=resp, steps=steps, event_ids=event_ids)

    final = "[agent exhausted max_iters]"
    return AgentRunResult(
        response=SkillResponse(text=final, raw={"adapter": adapter_name, "exhausted": True}),
        steps=steps + [{"type": "exhausted", "text": final}],
        event_ids=event_ids,
    )
