"""plugin_registry — 发现 + 注册 + 查询扩展点。

用法:
  from we_together.plugins import plugin_registry as pr
  pr.discover()           # 扫描 entry_points + 手动注册的 plugin
  pr.list_by_kind("importer")
  pr.register("service", my_service_instance)   # 手动注册（测试用）
  pr.get_by_name("importer", "slack_importer")
  pr.status()

隔离原则：
- discover 错误不 raise；记 errors 列表
- get_by_name 找不到返回 None
- list_by_kind 只返回加载成功的
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from we_together.plugins import (
    ENTRY_POINT_GROUPS,
    PLUGIN_API_VERSION,
    PluginLoadError,
)


@dataclass
class RegistryEntry:
    kind: str
    name: str
    plugin: Any
    source: str = "manual"      # "manual" / "entry_point:{dist}" / "builtin"
    enabled: bool = True


@dataclass
class LoadError:
    kind: str
    ref: str
    reason: str


_lock = threading.Lock()
_entries: list[RegistryEntry] = []
_errors: list[LoadError] = []
_discovered = False


def _is_valid_plugin(plugin: Any, kind: str) -> tuple[bool, str]:
    """最小校验：plugin 必须有 name 字段与 plugin_api_version。"""
    if not hasattr(plugin, "name") or not getattr(plugin, "name"):
        return False, "missing attribute: name"
    version = getattr(plugin, "plugin_api_version", None)
    if version is None:
        return False, "missing attribute: plugin_api_version"
    if str(version) != PLUGIN_API_VERSION:
        return False, f"plugin_api_version {version!r} != expected {PLUGIN_API_VERSION!r}"
    if kind == "hook" and not getattr(plugin, "event_type", None):
        return False, "hook plugin missing event_type"
    if kind == "provider" and not getattr(plugin, "provider_kind", None):
        return False, "provider plugin missing provider_kind"
    return True, ""


def register(kind: str, plugin: Any, *, source: str = "manual") -> RegistryEntry:
    if kind not in ENTRY_POINT_GROUPS:
        raise ValueError(f"unknown plugin kind: {kind}")
    ok, reason = _is_valid_plugin(plugin, kind)
    if not ok:
        raise PluginLoadError(getattr(plugin, "name", "<unknown>"), reason)
    entry = RegistryEntry(kind=kind, name=plugin.name, plugin=plugin, source=source)
    with _lock:
        existing = next(
            (e for e in _entries if e.kind == kind and e.name == plugin.name),
            None,
        )
        if existing:
            # 替换（manual register 可覆盖 entry_point）
            _entries.remove(existing)
        _entries.append(entry)
    return entry


def unregister(kind: str, name: str) -> bool:
    with _lock:
        before = len(_entries)
        _entries[:] = [e for e in _entries if not (e.kind == kind and e.name == name)]
        return len(_entries) < before


def disable(kind: str, name: str) -> bool:
    with _lock:
        for e in _entries:
            if e.kind == kind and e.name == name:
                e.enabled = False
                return True
    return False


def enable(kind: str, name: str) -> bool:
    with _lock:
        for e in _entries:
            if e.kind == kind and e.name == name:
                e.enabled = True
                return True
    return False


def discover(*, reload: bool = False) -> dict:
    """扫描 Python entry_points 四个 group，加载插件。

    返回 {"loaded": N, "failed": M, "errors": [...]}。
    """
    global _discovered
    try:
        import importlib.metadata as md
    except ImportError:  # pragma: no cover
        return {"loaded": 0, "failed": 0, "errors": [], "skipped": True}

    if _discovered and not reload:
        return status()

    loaded = 0
    failed = 0
    # 清掉旧 entry_point 记录（manual 的保留）
    with _lock:
        _entries[:] = [e for e in _entries if e.source == "manual"]
        _errors.clear()

    for kind, group in ENTRY_POINT_GROUPS.items():
        try:
            eps = md.entry_points(group=group)
        except TypeError:  # pragma: no cover Python < 3.10
            eps = md.entry_points().get(group, [])  # type: ignore[attr-defined]
        for ep in eps:
            ref = f"{ep.name}={ep.value}"
            try:
                plugin_cls_or_obj = ep.load()
                plugin = plugin_cls_or_obj() if callable(plugin_cls_or_obj) else plugin_cls_or_obj
                entry = register(kind, plugin, source=f"entry_point:{ep.name}")
                loaded += 1
            except Exception as exc:
                failed += 1
                _errors.append(LoadError(kind=kind, ref=ref, reason=str(exc)))
    _discovered = True
    return {"loaded": loaded, "failed": failed,
            "errors": [{"kind": e.kind, "ref": e.ref, "reason": e.reason}
                       for e in _errors]}


def list_by_kind(kind: str, *, include_disabled: bool = False) -> list[RegistryEntry]:
    with _lock:
        return [
            e for e in _entries
            if e.kind == kind and (include_disabled or e.enabled)
        ]


def get_by_name(kind: str, name: str) -> RegistryEntry | None:
    with _lock:
        for e in _entries:
            if e.kind == kind and e.name == name:
                return e
    return None


def status() -> dict:
    with _lock:
        by_kind: dict[str, list[dict]] = {}
        for e in _entries:
            by_kind.setdefault(e.kind, []).append({
                "name": e.name, "source": e.source, "enabled": e.enabled,
            })
        return {
            "plugin_api_version": PLUGIN_API_VERSION,
            "total_registered": len(_entries),
            "by_kind": by_kind,
            "load_errors": [
                {"kind": e.kind, "ref": e.ref, "reason": e.reason}
                for e in _errors
            ],
        }


def reset() -> None:
    """测试用：清空 registry。"""
    global _discovered
    with _lock:
        _entries.clear()
        _errors.clear()
        _discovered = False
