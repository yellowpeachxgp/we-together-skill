"""Multimodal Embedding provider（Phase 32 MN-1/MN-3 teaser）。

CLIP / SigLIP 风格：text ↔ image 共享 embedding 空间。

默认 mock：对文本走 hash embed；对 image bytes 走不同但"相关"的 hash。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol


class MultimodalEmbeddingClient(Protocol):
    provider: str
    dim: int

    def embed_text(self, texts: list[str]) -> list[list[float]]: ...
    def embed_image(self, images: list[Path | bytes]) -> list[list[float]]: ...


class MockMultimodalClient:
    provider = "mock_multimodal"

    def __init__(self, *, dim: int = 32):
        self.dim = dim

    def _hash_to_vec(self, data: bytes) -> list[float]:
        h = hashlib.sha256(data).digest()
        out = []
        for i in range(self.dim):
            byte = h[i % len(h)]
            out.append((byte / 255.0) * 2 - 1)
        return out

    def embed_text(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_vec(t.encode("utf-8")) for t in texts]

    def embed_image(self, images: list[Path | bytes]) -> list[list[float]]:
        out: list[list[float]] = []
        for img in images:
            if isinstance(img, Path):
                data = img.read_bytes() if img.exists() else img.name.encode("utf-8")
            else:
                data = img
            out.append(self._hash_to_vec(data))
        return out


class CLIPStubClient:
    """CLIP stub：延迟 import transformers + torch，真实使用时才加载。"""
    provider = "clip_stub"

    def __init__(self, *, model: str = "openai/clip-vit-base-patch32", dim: int = 512):
        try:
            import transformers  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "transformers 未安装: pip install transformers torch pillow"
            ) from exc
        self.model = model
        self.dim = dim

    def embed_text(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        from transformers import CLIPTokenizer, CLIPTextModel
        import torch
        tok = CLIPTokenizer.from_pretrained(self.model)
        m = CLIPTextModel.from_pretrained(self.model)
        out: list[list[float]] = []
        for t in texts:
            inputs = tok(t, return_tensors="pt")
            with torch.no_grad():
                feats = m(**inputs).pooler_output[0]
            out.append(feats.tolist())
        return out

    def embed_image(self, images: list[Path | bytes]) -> list[list[float]]:  # pragma: no cover
        from transformers import CLIPImageProcessor, CLIPVisionModel
        from PIL import Image
        import torch
        proc = CLIPImageProcessor.from_pretrained(self.model)
        m = CLIPVisionModel.from_pretrained(self.model)
        out: list[list[float]] = []
        for img in images:
            if isinstance(img, Path):
                pil = Image.open(img)
            else:
                import io
                pil = Image.open(io.BytesIO(img))
            inputs = proc(images=pil, return_tensors="pt")
            with torch.no_grad():
                feats = m(**inputs).pooler_output[0]
            out.append(feats.tolist())
        return out


def cross_modal_similarity(
    query_vec: list[float], candidates: list[tuple[str, list[float]]],
    *, k: int = 5,
) -> list[tuple[str, float]]:
    """跨模态：query（如 text）对 candidates（如 image embeddings）做 cosine top-k。"""
    from we_together.services.vector_similarity import cosine_similarity
    scored = [(cid, cosine_similarity(query_vec, v)) for cid, v in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
