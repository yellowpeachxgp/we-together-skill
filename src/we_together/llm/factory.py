"""LLM provider 工厂：按环境/配置返回具体客户端。"""
from __future__ import annotations

import os

from we_together.llm.client import LLMClient


def get_llm_client(provider: str | None = None, **kwargs) -> LLMClient:
    """按优先级解析 provider：
    1. 显式传入的 provider 参数
    2. 环境变量 WE_TOGETHER_LLM_PROVIDER
    3. 默认 "mock"
    """
    name = provider or os.environ.get("WE_TOGETHER_LLM_PROVIDER", "mock")
    name = name.lower().strip()

    if name == "mock":
        from we_together.llm.providers.mock import MockLLMClient
        return MockLLMClient(**kwargs)
    if name == "anthropic":
        from we_together.llm.providers.anthropic import AnthropicLLMClient
        return AnthropicLLMClient(**kwargs)
    if name in ("openai", "openai_compat"):
        from we_together.llm.providers.openai_compat import OpenAICompatClient
        return OpenAICompatClient(**kwargs)

    raise ValueError(f"Unknown LLM provider: {name}")
