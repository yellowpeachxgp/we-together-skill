"""Audio importer：转写 → narration 文本 → candidate 层。"""
from __future__ import annotations

from pathlib import Path

from we_together.llm.providers.audio import AudioTranscriber


def import_audio(
    audio_path: Path,
    transcriber: AudioTranscriber,
    *,
    language: str | None = None,
    source_name: str | None = None,
) -> dict:
    if not audio_path.exists():
        raise FileNotFoundError(f"audio not found: {audio_path}")
    transcript = transcriber.transcribe(audio_path, language=language)
    return {
        "identity_candidates": [],
        "event_candidates": [
            {
                "summary": transcript[:500] or "[empty transcript]",
                "event_type": "audio_event",
                "timestamp": None,
                "confidence": 0.55,
                "source": "audio_importer",
                "audio_path": str(audio_path),
                "language": language,
            }
        ],
        "source": "audio_importer",
        "transcript": transcript,
        "transcript_length": len(transcript),
    }
