"""Streaming SkillResponse：支持分块输出的响应对象。

Phase 23 IT-3：让 adapter 能流式返回（text chunk），chat_service / bot 边收边回显。
不改变既有 SkillResponse 契约，而是并存。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Iterator


@dataclass
class StreamingSkillResponse:
    """包裹一个 chunk iterable。最终调用 `.finalize()` 得到等价 SkillResponse。

    典型用法:
      resp = adapter.invoke_stream(request, llm_client)
      for chunk in resp:
          print(chunk, end="", flush=True)
      final = resp.finalize()  # SkillResponse
    """
    chunks: Iterable[str]
    speaker_person_id: str | None = None
    supporting_speakers: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    _buffer: list[str] = field(default_factory=list)
    _consumed: bool = False

    def __iter__(self) -> Iterator[str]:
        for c in self.chunks:
            self._buffer.append(c)
            yield c
        self._consumed = True

    def finalize(self):
        from we_together.runtime.skill_runtime import SkillResponse
        if not self._consumed:
            # 自动 drain
            for _ in self:
                pass
        return SkillResponse(
            text="".join(self._buffer),
            speaker_person_id=self.speaker_person_id,
            supporting_speakers=list(self.supporting_speakers),
            usage=dict(self.usage),
            raw=dict(self.raw),
        )


def mock_stream_chunks(text: str, *, chunk_size: int = 4) -> Iterator[str]:
    """测试用：按 chunk_size 把完整文本切成块。"""
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
