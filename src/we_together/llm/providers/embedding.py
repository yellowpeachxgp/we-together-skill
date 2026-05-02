"""Embedding provider 抽象（延迟 import 真 SDK）。

- EmbeddingClient Protocol
- MockEmbeddingClient（确定性 hash 输出，适合测试）
- OpenAIEmbeddingClient / SentenceTransformersClient stub
"""
from __future__ import annotations

import hashlib
import os
from typing import Protocol


class EmbeddingClient(Protocol):
    provider: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class MockEmbeddingClient:
    """确定性 mock：把字符串 hash 映射到 dim 维向量。同文本 → 同向量。"""
    provider = "mock_embedding"

    def __init__(self, *, dim: int = 16):
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_vec(t) for t in texts]

    def _hash_to_vec(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode("utf-8")).digest()
        out = []
        for i in range(self.dim):
            byte = h[i % len(h)]
            out.append((byte / 255.0) * 2 - 1)  # [-1, 1]
        return out


class OpenAIEmbeddingClient:
    provider = "openai_embedding"

    def __init__(self, *, api_key: str | None = None,
                 model: str = "text-embedding-3-small", dim: int = 1536):
        try:
            import openai  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("openai 未安装: pip install openai") from exc
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY") or "dummy"
        self.model = model
        self.dim = dim
        import openai as _openai
        self._client = _openai.OpenAI(api_key=self._api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        resp = self._client.embeddings.create(model=self.model, input=texts)
        return [d.embedding for d in resp.data]


class SentenceTransformersClient:
    provider = "sentence_transformers"

    def __init__(self, *, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "sentence-transformers 未安装: pip install sentence-transformers"
            ) from exc
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model)
        self.dim = int(self._model.get_sentence_embedding_dimension())

    def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        return [list(v) for v in self._model.encode(texts)]
