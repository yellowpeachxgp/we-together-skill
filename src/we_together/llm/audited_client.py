"""Usage-audited LLM wrapper.

把 LLM 调用包装为可审计的 usage / token / 粗略成本统计，
优先使用 provider 原生 usage，没有则回退到估算。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from we_together.llm.client import LLMMessage, LLMResponse
from we_together.services.tick_cost_tracker import TickCostTracker


def estimate_cost_usd(
    usage_summary: dict,
    *,
    prompt_price_per_1k: float = 0.0,
    completion_price_per_1k: float = 0.0,
) -> float:
    by_provider = usage_summary.get("by_provider", {})
    prompt_tokens = sum(int(v.get("prompt_tokens", 0)) for v in by_provider.values())
    completion_tokens = sum(int(v.get("completion_tokens", 0)) for v in by_provider.values())
    cost = (prompt_tokens / 1000.0) * prompt_price_per_1k
    cost += (completion_tokens / 1000.0) * completion_price_per_1k
    return round(cost, 6)


@dataclass
class UsageAuditedLLMClient:
    base_client: object
    tracker: TickCostTracker = field(default_factory=TickCostTracker)

    @property
    def provider(self) -> str:
        return getattr(self.base_client, "provider", "unknown")

    def _messages_to_text(self, messages: list[LLMMessage]) -> str:
        return "\n".join(m.content for m in messages)

    def _track(self, *, usage: dict | None, text_in: str, text_out: str) -> None:
        usage = usage or {}
        prompt_tokens = int(
            usage.get("prompt_tokens")
            or usage.get("input_tokens")
            or 0
        )
        completion_tokens = int(
            usage.get("completion_tokens")
            or usage.get("output_tokens")
            or 0
        )
        if prompt_tokens > 0 or completion_tokens > 0:
            self.tracker.track(
                self.provider,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            return
        self.tracker.track_estimated(
            self.provider,
            text_in=text_in,
            text_out=text_out,
        )

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        resp = self.base_client.chat(messages, **kwargs)
        self._track(
            usage=getattr(resp, "usage", None),
            text_in=self._messages_to_text(messages),
            text_out=resp.content,
        )
        return resp

    def chat_json(self, messages: list[LLMMessage], schema_hint: dict | str, **kwargs) -> dict:
        payload = self.base_client.chat_json(messages, schema_hint, **kwargs)
        self._track(
            usage=None,
            text_in=self._messages_to_text(messages),
            text_out=json.dumps(payload, ensure_ascii=False),
        )
        return payload

    def summary(self) -> dict:
        return self.tracker.summary()
