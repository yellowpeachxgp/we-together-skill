"""Anthropic Claude provider。

Phase 25 扩展:
  - chat_with_tools: 原生 content_block + tool_use 解析
  - chat_stream: with client.messages.stream()
"""
from __future__ import annotations

import os
from typing import Iterator

from we_together.llm.client import LLMMessage, LLMResponse
from we_together.llm.providers.mock import parse_json_loose


class AnthropicLLMClient:
    provider = "anthropic"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
    ):
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "anthropic SDK not installed. `pip install anthropic` or use mock provider."
            ) from exc
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        self.model = model
        self.max_tokens = max_tokens
        import anthropic as _anthropic
        self._client = _anthropic.Anthropic(api_key=self._api_key)

    def _split_messages(self, messages: list[LLMMessage]) -> tuple[str, list[dict]]:
        system_parts = [m.content for m in messages if m.role == "system"]
        others = [
            {"role": m.role, "content": m.content}
            for m in messages if m.role != "system"
        ]
        return "\n\n".join(system_parts), others

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:  # pragma: no cover
        system, msgs = self._split_messages(messages)
        resp = self._client.messages.create(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            system=system or None,
            messages=msgs,
        )
        content = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        return LLMResponse(
            content=content,
            model=getattr(resp, "model", self.model),
            usage=getattr(resp, "usage", {}).__dict__ if hasattr(resp, "usage") else {},
            raw={"id": getattr(resp, "id", None)},
        )

    def chat_json(
        self, messages: list[LLMMessage], schema_hint: dict | str, **kwargs,
    ) -> dict:  # pragma: no cover
        guard = (
            "Return ONLY a valid JSON object matching this schema hint. "
            f"No explanation. Schema: {schema_hint}"
        )
        augmented = list(messages) + [LLMMessage(role="user", content=guard)]
        resp = self.chat(augmented, **kwargs)
        return parse_json_loose(resp.content)

    def chat_with_tools(
        self, messages: list[LLMMessage], tools: list[dict], **kwargs,
    ) -> dict:  # pragma: no cover
        """原生 Anthropic tool_use：解析 content_block 的 text / tool_use。"""
        system, msgs = self._split_messages(messages)
        resp = self._client.messages.create(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            system=system or None,
            messages=msgs,
            tools=tools or None,
        )
        texts = []
        tool_uses = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                texts.append(block.text)
            elif btype == "tool_use":
                tool_uses.append({
                    "id": getattr(block, "id", ""),
                    "name": getattr(block, "name", ""),
                    "input": dict(getattr(block, "input", {}) or {}),
                })
        return {
            "text": "".join(texts),
            "tool_uses": tool_uses,
            "stop_reason": getattr(resp, "stop_reason", "end_turn"),
            "raw": {"id": getattr(resp, "id", None)},
        }

    def chat_stream(
        self, messages: list[LLMMessage], **kwargs,
    ) -> Iterator[str]:  # pragma: no cover
        system, msgs = self._split_messages(messages)
        with self._client.messages.stream(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            system=system or None,
            messages=msgs,
        ) as stream:
            for chunk in stream.text_stream:
                yield chunk
