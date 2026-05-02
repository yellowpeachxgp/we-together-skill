"""Embedding LRU cache：避免重复 embed 相同文本。"""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Iterable


class EmbeddingLRUCache:
    """简单 LRU + TTL cache。"""

    def __init__(self, *, maxsize: int = 1024, ttl_seconds: int = 3600):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._data: "OrderedDict[str, tuple[float, list[float]]]" = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, text: str) -> list[float] | None:
        now = time.time()
        if text in self._data:
            ts, vec = self._data[text]
            if now - ts <= self.ttl_seconds:
                self._data.move_to_end(text)
                self.hits += 1
                return vec
            del self._data[text]
        self.misses += 1
        return None

    def put(self, text: str, vec: list[float]) -> None:
        self._data[text] = (time.time(), vec)
        self._data.move_to_end(text)
        while len(self._data) > self.maxsize:
            self._data.popitem(last=False)

    def embed_with_cache(
        self, texts: Iterable[str], embedding_client,
    ) -> list[list[float]]:
        texts = list(texts)
        results: list[list[float]] = [None] * len(texts)  # type: ignore
        # dedup miss：同一 text 只算一次 miss + 一次 embed
        missing_idx_by_text: "OrderedDict[str, list[int]]" = OrderedDict()
        for i, t in enumerate(texts):
            hit = self.get(t)
            if hit is not None:
                results[i] = hit
            else:
                if t in missing_idx_by_text:
                    # 同批内已记过 miss，后续算 hit（batch-level dedup）
                    missing_idx_by_text[t].append(i)
                    self.misses -= 1
                    self.hits += 1
                else:
                    missing_idx_by_text[t] = [i]
        if missing_idx_by_text:
            miss_texts = list(missing_idx_by_text.keys())
            miss_vecs = embedding_client.embed(miss_texts)
            for text, vec in zip(miss_texts, miss_vecs):
                self.put(text, vec)
                for idx in missing_idx_by_text[text]:
                    results[idx] = vec
        return results

    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total > 0 else 0.0

    def emit_metrics(self) -> None:
        try:
            from we_together.observability.metrics import counter_inc, gauge_set
            counter_inc("embedding_cache_hits", value=float(self.hits))
            counter_inc("embedding_cache_misses", value=float(self.misses))
            gauge_set("embedding_cache_hit_rate", self.hit_rate())
        except Exception:
            pass
