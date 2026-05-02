"""OpenAI-compatible provider。

Phase 25 扩展:
  - chat_with_tools: message.tool_calls 解析
  - chat_stream: stream=True
"""
from __future__ import annotations

import json
import os
from typing import Iterator

from we_together.llm.client import LLMMessage, LLMResponse
from we_together.llm.providers.mock import parse_json_loose


class OpenAICompatClient:
    provider = "openai_compat"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 4096,
    ):
        try:
            import openai  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "openai SDK not installed. `pip install openai` or use mock provider."
            ) from exc
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY") or "dummy"
        self._base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self.model = model
        self.max_tokens = max_tokens
        import openai as _openai
        client_kwargs = {"api_key": self._api_key}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        self._client = _openai.OpenAI(**client_kwargs)

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:  # pragma: no cover
        payload = [{"role": m.role, "content": m.content} for m in messages]
        resp = self._client.chat.completions.create(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            messages=payload,
        )
        choice = resp.choices[0]
        content = choice.message.content or ""
        usage = {}
        if getattr(resp, "usage", None):
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
            }
        return LLMResponse(content=content, model=resp.model, usage=usage,
                            raw={"id": resp.id})

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
        """原生 OpenAI tool_calls：解析 choice.message.tool_calls。

        期望 tools 已经是 OpenAI function schema。
        """
        payload = [{"role": m.role, "content": m.content} for m in messages]
        resp = self._client.chat.completions.create(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            messages=payload,
            tools=tools or None,
        )
        choice = resp.choices[0]
        message = choice.message
        tool_uses = []
        for tc in getattr(message, "tool_calls", None) or []:
            fn = getattr(tc, "function", None)
            if fn is None:
                continue
            try:
                args = json.loads(fn.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_uses.append({
                "id": getattr(tc, "id", ""),
                "name": fn.name,
                "input": args,
            })
        stop_reason = "tool_use" if tool_uses else "end_turn"
        return {
            "text": message.content or "",
            "tool_uses": tool_uses,
            "stop_reason": stop_reason,
            "raw": {"id": resp.id},
        }

    def chat_stream(
        self, messages: list[LLMMessage], **kwargs,
    ) -> Iterator[str]:  # pragma: no cover
        payload = [{"role": m.role, "content": m.content} for m in messages]
        stream = self._client.chat.completions.create(
            model=kwargs.get("model", self.model),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            messages=payload,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta:
                delta_text = chunk.choices[0].delta.content or ""
                if delta_text:
                    yield delta_text
