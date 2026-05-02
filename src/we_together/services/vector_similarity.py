"""Vector similarity 工具：cosine / top_k / BLOB 编解码。

纯 Python 实现，不依赖 numpy。真实规模建议用 FAISS/chromadb 替换。
"""
from __future__ import annotations

import math
import struct


def encode_vec(vec: list[float]) -> bytes:
    """把 float list 编码为 float32 BLOB。"""
    return struct.pack(f"<{len(vec)}f", *vec)


def decode_vec(blob: bytes | bytearray | memoryview) -> list[float]:
    """解码 float32 BLOB 回 float list。"""
    blob = bytes(blob)
    count = len(blob) // 4
    return list(struct.unpack(f"<{count}f", blob))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def top_k(
    query: list[float],
    candidates: list[tuple[str, list[float]]],
    *,
    k: int = 5,
) -> list[tuple[str, float]]:
    """返回 [(id, similarity), ...] 按 similarity 降序的 top-k。"""
    scored = [(cid, cosine_similarity(query, vec)) for cid, vec in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
