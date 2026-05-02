"""Screenshot series importer：连续截图 → VLM → 时间轴事件流。"""
from __future__ import annotations

from pathlib import Path

from we_together.llm.providers.vision import VisionLLMClient


def import_screenshot_series(
    *,
    screenshots: list[tuple[float, Path]],  # [(timestamp, path), ...]
    vision_client: VisionLLMClient,
    prompt: str = "描述截图内容及其中关键信息。",
) -> dict:
    events: list[dict] = []
    for ts, path in sorted(screenshots, key=lambda x: x[0]):
        if not path.exists():
            continue
        description = vision_client.describe_image(path, prompt=prompt)
        events.append({
            "summary": description[:300],
            "event_type": "screenshot_event",
            "timestamp": ts,
            "confidence": 0.5,
            "source": "screenshot_series_importer",
            "screenshot_path": str(path),
        })
    return {
        "identity_candidates": [],
        "event_candidates": events,
        "source": "screenshot_series_importer",
        "screenshot_count": len(events),
    }
