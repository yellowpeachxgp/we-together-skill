"""Observability LLM hooks：before_call / after_call 两个钩子。

典型用法:
  from we_together.observability.llm_hooks import register_hook
  register_hook(my_hook)

  # 每次 LLM call 完成后 my_hook(event) 被调用:
  event = {
      "provider": "anthropic",
      "method": "chat_with_tools",
      "duration_ms": 123,
      "usage": {...},
      "tool_uses": [...],
  }
"""
from __future__ import annotations

import time
from typing import Callable

_hooks: list[Callable[[dict], None]] = []


def register_hook(hook: Callable[[dict], None]) -> None:
    _hooks.append(hook)


def clear_hooks() -> None:
    _hooks.clear()


def emit(event: dict) -> None:
    for h in _hooks:
        try:
            h(dict(event))
        except Exception:
            pass


class timed_call:
    """Context manager：记录 LLM call 耗时并 emit hook。"""

    def __init__(self, *, provider: str, method: str, extra: dict | None = None):
        self.provider = provider
        self.method = method
        self.extra = extra or {}
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        duration_ms = (time.time() - self._t0) * 1000
        emit({
            "provider": self.provider,
            "method": self.method,
            "duration_ms": round(duration_ms, 2),
            "error": exc is not None,
            "error_msg": str(exc) if exc else None,
            **self.extra,
        })
        return False


class LangSmithStubSink:
    """LangSmith stub sink：记录事件到内存列表。

    真实 LangSmith 接入需要 pip install langsmith，延迟导入在使用时处理。
    """
    def __init__(self) -> None:
        self.events: list[dict] = []

    def __call__(self, event: dict) -> None:
        self.events.append(dict(event))
