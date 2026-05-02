"""LLM adapter 抽象层。

设计原则：
- 核心路径不直接 import 任何平台 SDK；provider 延迟加载
- Mock provider 用于所有单元测试，保证测试无需网络/API Key
- 配置通过环境变量 WE_TOGETHER_LLM_PROVIDER 切换（mock/anthropic/openai_compat）
- JSON mode 以最小契约提供：输入 prompt + schema hint，返回解析后的 dict
"""
from we_together.llm.client import (
    JSONExtractionError,
    LLMClient,
    LLMMessage,
    LLMResponse,
)
from we_together.llm.factory import get_llm_client

__all__ = [
    "LLMClient",
    "LLMMessage",
    "LLMResponse",
    "JSONExtractionError",
    "get_llm_client",
]
