"""Vision LLM provider (mock + Anthropic stub)。

设计：
  - VisionLLMClient Protocol：describe_image(image_path or bytes) -> str
  - MockVisionLLMClient：scripted_descriptions 或 default
  - AnthropicVisionClient：延迟 import anthropic SDK；实例化时才加载
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class VisionLLMClient(Protocol):
    provider: str

    def describe_image(self, image: Path | bytes, *, prompt: str = "") -> str: ...


class MockVisionLLMClient:
    provider = "mock_vision"

    def __init__(self, *, scripted_descriptions: list[str] | None = None,
                 default_description: str = "[mock image description]"):
        self._scripted = list(scripted_descriptions or [])
        self.default = default_description
        self.calls: list[dict] = []

    def describe_image(self, image: Path | bytes, *, prompt: str = "") -> str:
        self.calls.append({"image": str(image) if isinstance(image, Path) else "<bytes>",
                            "prompt": prompt})
        if self._scripted:
            return self._scripted.pop(0)
        return self.default


class AnthropicVisionClient:
    provider = "anthropic_vision"

    def __init__(self, *, api_key: str | None = None, model: str = "claude-opus-4-7"):
        try:
            import anthropic  # noqa: F401 延迟 import
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("anthropic SDK not installed") from exc
        self.api_key = api_key
        self.model = model

    def describe_image(self, image: Path | bytes, *, prompt: str = "") -> str:  # pragma: no cover
        import anthropic
        import base64
        client = anthropic.Anthropic(api_key=self.api_key)
        if isinstance(image, Path):
            data = image.read_bytes()
        else:
            data = image
        b64 = base64.b64encode(data).decode("ascii")
        resp = client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                    {"type": "text", "text": prompt or "描述这张图并指出其中出现的人物、物件与关系。"},
                ],
            }],
        )
        return resp.content[0].text if resp.content else ""
