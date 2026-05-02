"""Mock LLM provider：用于所有单元测试和无 API Key 场景降级。

Phase 25：扩展 chat_with_tools / chat_stream 支持 tool_use + streaming 模拟。
"""
from __future__ import annotations

import json
from typing import Iterator

from we_together.llm.client import (
    JSONExtractionError,
    LLMMessage,
    LLMResponse,
)


class MockLLMClient:
    provider = "mock"

    def __init__(
        self,
        *,
        scripted_responses: list[str] | None = None,
        scripted_json: list[dict] | None = None,
        scripted_tool_uses: list[dict] | None = None,
        scripted_stream: list[list[str]] | None = None,
        default_content: str = "[mock response]",
        default_json: dict | None = None,
    ):
        self._scripted_responses = list(scripted_responses or [])
        self._scripted_json = list(scripted_json or [])
        self._scripted_tool_uses = list(scripted_tool_uses or [])
        self._scripted_stream = list(scripted_stream or [])
        self.default_content = default_content
        self.default_json = default_json if default_json is not None else {"mock": True}
        self.calls: list[dict] = []

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        self.calls.append({"type": "chat", "messages": messages, "kwargs": kwargs})
        if self._scripted_responses:
            content = self._scripted_responses.pop(0)
        else:
            content = self.default_content
        return LLMResponse(content=content, model="mock", usage={}, raw={})

    def chat_json(
        self,
        messages: list[LLMMessage],
        schema_hint: dict | str,
        **kwargs,
    ) -> dict:
        self.calls.append({
            "type": "chat_json",
            "messages": messages,
            "schema_hint": schema_hint,
            "kwargs": kwargs,
        })
        if self._scripted_json:
            return self._scripted_json.pop(0)
        return dict(self.default_json)

    def chat_with_tools(
        self,
        messages: list[LLMMessage],
        tools: list[dict],
        **kwargs,
    ) -> dict:
        """返回 {text, tool_uses, stop_reason, raw}。

        scripted_tool_uses 每项 dict 形如:
          {"text": "...", "tool_uses": [{"id": "...", "name": "...", "input": {...}}],
           "stop_reason": "tool_use" | "end_turn"}
        """
        self.calls.append({
            "type": "chat_with_tools",
            "messages": messages,
            "tools": tools,
            "kwargs": kwargs,
        })
        if self._scripted_tool_uses:
            return dict(self._scripted_tool_uses.pop(0))
        return {
            "text": self.default_content,
            "tool_uses": [],
            "stop_reason": "end_turn",
            "raw": {},
        }

    def chat_stream(
        self, messages: list[LLMMessage], **kwargs,
    ) -> Iterator[str]:
        """流式 chat：yield 文本 chunk。"""
        self.calls.append({"type": "chat_stream", "messages": messages,
                            "kwargs": kwargs})
        if self._scripted_stream:
            for c in self._scripted_stream.pop(0):
                yield c
        else:
            for i in range(0, len(self.default_content), 4):
                yield self.default_content[i:i + 4]

    def queue_response(self, content: str) -> None:
        self._scripted_responses.append(content)

    def queue_json(self, payload: dict) -> None:
        self._scripted_json.append(payload)

    def queue_tool_use(self, payload: dict) -> None:
        self._scripted_tool_uses.append(payload)

    def queue_stream(self, chunks: list[str]) -> None:
        self._scripted_stream.append(chunks)


def parse_json_loose(text: str) -> dict:
    """尝试从 LLM 响应中抽取 JSON 对象。"""
    text = text.strip()
    if text.startswith("```"):
        inner = text.strip("`")
        if inner.lower().startswith("json"):
            inner = inner[4:]
        text = inner.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise JSONExtractionError(f"no JSON object found in: {text[:80]!r}")
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise JSONExtractionError(str(exc)) from exc
