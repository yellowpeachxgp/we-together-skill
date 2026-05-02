"""tick_cost_tracker（Phase 39 CT-5/6）：估算 tick 内 LLM 调用的 token / 成本。

不真调 API；只做**调用次数与估算 token** 的会计。真成本需乘上 provider 单价（不硬编）。

职责：
- track_llm_call(provider, prompt_tokens, completion_tokens)
- summarize() → 总调用次数 / 总 token / 按 provider 分档
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class CostSample:
    provider: str
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class TickCostTracker:
    samples: list[CostSample] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def track(self, provider: str, *, prompt_tokens: int, completion_tokens: int) -> None:
        with self._lock:
            self.samples.append(CostSample(provider, prompt_tokens, completion_tokens))

    def track_estimated(self, provider: str, *, text_in: str, text_out: str) -> None:
        """粗估 token：按字符/4（英文）或字数（中文）近似。
        不替代真 tokenizer；用于 Mock LLM 路径的成本骨架。"""
        pin = max(1, len(text_in) // 4)
        pout = max(1, len(text_out) // 4)
        self.track(provider, prompt_tokens=pin, completion_tokens=pout)

    def summary(self) -> dict:
        total_calls = len(self.samples)
        total_tok = sum(s.total_tokens for s in self.samples)
        by_provider: dict[str, dict] = {}
        for s in self.samples:
            b = by_provider.setdefault(
                s.provider,
                {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0},
            )
            b["calls"] += 1
            b["prompt_tokens"] += s.prompt_tokens
            b["completion_tokens"] += s.completion_tokens
        return {
            "total_calls": total_calls,
            "total_tokens": total_tok,
            "by_provider": by_provider,
        }

    def reset(self) -> None:
        with self._lock:
            self.samples.clear()
