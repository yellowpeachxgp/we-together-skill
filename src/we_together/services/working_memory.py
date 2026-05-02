"""working_memory（Phase 55 DF-1/2）：短时记忆。

区分：
- long-term memory（memories 表）：持久、可召回、entering retrieval_package
- **working memory**：当前 scene / tick 内的高活性 context，过期即消失
  - 例：刚刚被激活的 3 条 relation、最近一轮对话 transcript、当前 drive

设计：
- **不落 db**（短时）；存 in-memory 或缓存到 retrieval_cache
- 每个 scene 有自己的 working_memory buffer
- TTL: 默认 300s；超期被 GC
- 不变式 #28 前置：working_memory 是**派生**，不能成为唯一真相；随时可从底层 memory/event 重建
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class WorkingMemoryItem:
    content: str
    kind: str = "note"               # note / recall / drive / transcript_chunk / ...
    weight: float = 1.0
    source_refs: list[str] = field(default_factory=list)   # memory_id / event_id / drive_id
    ttl_seconds: float = 300.0
    created_at: float = field(default_factory=time.monotonic)

    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) >= self.ttl_seconds

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "kind": self.kind,
            "weight": self.weight,
            "source_refs": list(self.source_refs),
            "age_seconds": round(time.monotonic() - self.created_at, 2),
            "expires_in_seconds": max(
                0.0,
                round(self.ttl_seconds - (time.monotonic() - self.created_at), 2),
            ),
        }


class WorkingMemoryBuffer:
    def __init__(self, *, scene_id: str, capacity: int = 20):
        self.scene_id = scene_id
        self.capacity = capacity
        self._items: list[WorkingMemoryItem] = []
        self._lock = threading.Lock()

    def add(self, item: WorkingMemoryItem) -> None:
        with self._lock:
            self._items.append(item)
            self._prune_locked()

    def add_note(
        self, content: str, *,
        kind: str = "note", weight: float = 1.0,
        source_refs: list[str] | None = None,
        ttl_seconds: float = 300.0,
    ) -> WorkingMemoryItem:
        item = WorkingMemoryItem(
            content=content, kind=kind, weight=weight,
            source_refs=list(source_refs or []),
            ttl_seconds=ttl_seconds,
        )
        self.add(item)
        return item

    def _prune_locked(self) -> None:
        # 删过期
        self._items = [x for x in self._items if not x.is_expired()]
        # 超容量按 weight + recency 去掉最低
        if len(self._items) > self.capacity:
            self._items.sort(
                key=lambda x: (x.weight, -(time.monotonic() - x.created_at)),
                reverse=True,
            )
            self._items = self._items[: self.capacity]

    def snapshot(self) -> list[dict]:
        with self._lock:
            self._prune_locked()
            return [it.to_dict() for it in self._items]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._items)


# --- 全局 registry（per-scene）---

_buffers: dict[str, WorkingMemoryBuffer] = {}
_reg_lock = threading.Lock()


def get_buffer(scene_id: str, *, capacity: int = 20) -> WorkingMemoryBuffer:
    with _reg_lock:
        buf = _buffers.get(scene_id)
        if buf is None:
            buf = WorkingMemoryBuffer(scene_id=scene_id, capacity=capacity)
            _buffers[scene_id] = buf
        return buf


def clear_all() -> None:
    """测试用。"""
    with _reg_lock:
        _buffers.clear()


def snapshot_all() -> dict[str, list[dict]]:
    with _reg_lock:
        return {sid: buf.snapshot() for sid, buf in _buffers.items()}
