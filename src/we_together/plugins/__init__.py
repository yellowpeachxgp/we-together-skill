"""we_together.plugins — 扩展点注册 + 加载。

Phase 44 / ADR 0046：第三方可通过 Python entry_points 注册 Importer / Service / Provider / Hook，
不需 fork we-together 核心。

设计：
- 4 个扩展点（entry_points group）：
    we_together.importers
    we_together.services
    we_together.providers
    we_together.hooks
- 每个扩展点必须返回一个符合对应 Protocol 的 callable / class
- 加载错误**隔离**：一个 plugin 失败不影响其他
- plugin_api_version 字段用于向后兼容（当前 "1"）
"""
from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable


PLUGIN_API_VERSION = "1"

ENTRY_POINT_GROUPS = {
    "importer": "we_together.importers",
    "service": "we_together.services",
    "provider": "we_together.providers",
    "hook": "we_together.hooks",
}


@runtime_checkable
class ImporterPlugin(Protocol):
    name: str
    plugin_api_version: str

    def run(self, *, source: str, db_path: Any) -> dict: ...


@runtime_checkable
class ServicePlugin(Protocol):
    name: str
    plugin_api_version: str

    def invoke(self, db_path: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class ProviderPlugin(Protocol):
    name: str
    provider_kind: str        # "llm" / "embedding" / "vision" / "audio" / ...
    plugin_api_version: str


@runtime_checkable
class HookPlugin(Protocol):
    name: str
    event_type: str           # "tick.before" / "tick.after" / "patch.applied" / ...
    plugin_api_version: str

    def handle(self, payload: dict) -> None: ...


PluginKind = str  # "importer" / "service" / "provider" / "hook"


class PluginLoadError(Exception):
    def __init__(self, plugin_ref: str, reason: str):
        super().__init__(f"plugin load failed: {plugin_ref} — {reason}")
        self.plugin_ref = plugin_ref
        self.reason = reason
