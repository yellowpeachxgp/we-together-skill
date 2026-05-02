"""Video importer：抽帧 (VLM 描述) + 音轨 (ASR) → 时间轴合并 event 序列。

最小实现：不真解视频容器。接受"帧路径列表 + 音频路径"分离输入。
真实使用时用 ffmpeg 预处理再传入。这让测试可无外部依赖地跑。
"""
from __future__ import annotations

from pathlib import Path

from we_together.llm.providers.audio import AudioTranscriber
from we_together.llm.providers.vision import VisionLLMClient


def import_video(
    *,
    frames: list[tuple[float, Path]],  # [(timestamp_sec, frame_path), ...]
    audio_path: Path | None,
    vision_client: VisionLLMClient,
    audio_transcriber: AudioTranscriber | None = None,
    source_name: str | None = None,
) -> dict:
    # 1. 帧描述
    frame_events: list[dict] = []
    for ts, fpath in frames:
        if not fpath.exists():
            continue
        description = vision_client.describe_image(
            fpath, prompt="描述画面内容与其中人物、关系。",
        )
        frame_events.append({
            "summary": description[:300],
            "event_type": "video_frame_event",
            "timestamp": ts,
            "confidence": 0.55,
            "source": "video_importer",
            "frame_path": str(fpath),
        })

    # 2. 音轨转写
    audio_events: list[dict] = []
    transcript = ""
    if audio_path and audio_transcriber:
        transcript = audio_transcriber.transcribe(audio_path)
        if transcript:
            audio_events.append({
                "summary": transcript[:500],
                "event_type": "video_audio_event",
                "timestamp": 0.0,
                "confidence": 0.55,
                "source": "video_importer",
                "audio_path": str(audio_path),
            })

    # 3. 合并时间轴（按 timestamp 升序）
    events = sorted(
        frame_events + audio_events,
        key=lambda e: (e.get("timestamp") or 0.0),
    )

    return {
        "identity_candidates": [],
        "event_candidates": events,
        "source": "video_importer",
        "frame_count": len(frame_events),
        "audio_transcript_length": len(transcript),
    }
