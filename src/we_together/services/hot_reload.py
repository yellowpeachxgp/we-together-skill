"""Skill 热加载：registry + invalidate/reload 钩子。

典型用法（MCP server）:
  reg = ReloadRegistry()
  reg.register("tools", load_tools_fn)
  reg.reload_all()   # 被 SIGHUP / file watcher 触发

本模块不依赖外部库；file_watcher 只做 polling 实现。
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class ReloadRegistry:
    handlers: dict[str, Callable[[], object]] = field(default_factory=dict)
    _last_values: dict[str, object] = field(default_factory=dict)

    def register(self, name: str, loader: Callable[[], object]) -> None:
        self.handlers[name] = loader
        self._last_values[name] = loader()

    def get(self, name: str) -> object:
        return self._last_values.get(name)

    def reload(self, name: str) -> object:
        if name not in self.handlers:
            raise KeyError(name)
        val = self.handlers[name]()
        self._last_values[name] = val
        return val

    def reload_all(self) -> dict[str, object]:
        return {n: self.reload(n) for n in self.handlers}


def poll_file_mtime(
    paths: list[Path], *, on_change: Callable[[Path], None],
    max_iters: int = 1, sleep_seconds: float = 0.0,
) -> int:
    """polling 文件变更通知（stdlib only）。

    max_iters + sleep_seconds 控制轮询行为：
      - 单次调用（默认）: iter=1 → 快照 + 和上次 snapshot 对比（此处第一次调用返回 0 变更）
      - 长期轮询（max_iters>1）: 间隔 sleep_seconds 轮询，发现变更就回调

    测试场景用 max_iters=1，业务场景外层包 while True。
    """
    snapshot: dict[Path, float] = {}
    for p in paths:
        if p.exists():
            snapshot[p] = p.stat().st_mtime
    changes = 0
    for _ in range(max_iters):
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
        for p in paths:
            if not p.exists():
                continue
            m = p.stat().st_mtime
            prev = snapshot.get(p)
            if prev is not None and m > prev:
                on_change(p)
                changes += 1
            snapshot[p] = m
    return changes
