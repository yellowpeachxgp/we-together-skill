"""图片 importer：用 VLM 描述图片内容 → candidate 层。

流程：
  1. VisionLLMClient.describe_image(path, prompt) → 描述文本
  2. 把描述写为 raw_evidence (source_type='image')
  3. 生成 event_candidate，summary=描述，可选 identity_candidates 来自启发式抽取
     （此处只做占位，真实 entity 抽取应该由 llm_extraction_service 二次处理）
"""
from __future__ import annotations

from pathlib import Path

from we_together.llm.providers.vision import VisionLLMClient


def import_image(
    image_path: Path,
    vision_client: VisionLLMClient,
    *,
    prompt: str = "描述这张图并指出其中出现的人物、物件与关系。",
) -> dict:
    if not image_path.exists():
        raise FileNotFoundError(f"image not found: {image_path}")
    description = vision_client.describe_image(image_path, prompt=prompt)
    return {
        "identity_candidates": [],
        "event_candidates": [
            {
                "summary": description,
                "event_type": "image_event",
                "timestamp": None,
                "confidence": 0.6,
                "source": "image_importer",
                "image_path": str(image_path),
            }
        ],
        "source": "image_importer",
        "description": description,
    }
