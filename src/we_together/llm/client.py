"""LLMClient 协议与核心数据结构。"""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str | None = None
    usage: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


class JSONExtractionError(ValueError):
    """LLM 返回的文本无法解析为 JSON。"""


class LLMClient(Protocol):
    """最小 LLM 契约。

    所有 provider 实现都必须提供:
      - chat(messages, **kwargs) -> LLMResponse
      - chat_json(messages, schema_hint, **kwargs) -> dict

    provider 名称作为 provider 属性暴露，便于日志和降级判断。
    """

    provider: str

    def chat(self, messages: list[LLMMessage], **kwargs) -> LLMResponse:
        ...

    def chat_json(
        self,
        messages: list[LLMMessage],
        schema_hint: dict | str,
        **kwargs,
    ) -> dict:
        ...
