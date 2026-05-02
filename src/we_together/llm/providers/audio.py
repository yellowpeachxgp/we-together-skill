"""Audio transcriber provider（ASR 抽象）。

Protocol + MockAudioTranscriber + stub Anthropic / OpenAI / Whisper backend。
与 llm/providers/vision.py 同样延迟 import 真实 SDK。
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class AudioTranscriber(Protocol):
    provider: str

    def transcribe(self, audio: Path | bytes, *, language: str | None = None) -> str: ...


class MockAudioTranscriber:
    provider = "mock_audio"

    def __init__(self, *, scripted_transcripts: list[str] | None = None,
                 default_transcript: str = "[mock transcript]"):
        self._scripted = list(scripted_transcripts or [])
        self.default = default_transcript
        self.calls: list[dict] = []

    def transcribe(self, audio: Path | bytes, *, language: str | None = None) -> str:
        self.calls.append({
            "audio": str(audio) if isinstance(audio, Path) else "<bytes>",
            "language": language,
        })
        if self._scripted:
            return self._scripted.pop(0)
        return self.default


class WhisperTranscriber:
    """OpenAI Whisper local stub：延迟 import whisper。"""
    provider = "whisper_local"

    def __init__(self, *, model: str = "base"):
        try:
            import whisper  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("whisper not installed: pip install openai-whisper") from exc
        self.model = model

    def transcribe(self, audio: Path | bytes, *, language: str | None = None) -> str:  # pragma: no cover
        import whisper
        model = whisper.load_model(self.model)
        result = model.transcribe(str(audio), language=language)
        return result.get("text", "")
