"""Phase 44 — Plugin 架构 (PL slices)。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


class _GoodImporter:
    name = "good_importer"
    plugin_api_version = "1"

    def run(self, *, source, db_path):
        return {"imported": source}


class _GoodService:
    name = "good_service"
    plugin_api_version = "1"

    def invoke(self, db_path, **kwargs):
        return {"db": str(db_path), **kwargs}


class _GoodProvider:
    name = "custom_llm"
    provider_kind = "llm"
    plugin_api_version = "1"


class _GoodHook:
    name = "tick_logger"
    event_type = "tick.after"
    plugin_api_version = "1"

    def handle(self, payload):
        pass


class _BadNoName:
    plugin_api_version = "1"


class _BadWrongVersion:
    name = "legacy"
    plugin_api_version = "0.9"


class _BadProviderNoKind:
    name = "weird_provider"
    plugin_api_version = "1"


class _BadHookNoEvent:
    name = "weird_hook"
    plugin_api_version = "1"

    def handle(self, p):
        pass


def test_register_and_list():
    from we_together.plugins import plugin_registry as pr
    pr.reset()
    pr.register("importer", _GoodImporter())
    pr.register("service", _GoodService())
    assert len(pr.list_by_kind("importer")) == 1
    assert len(pr.list_by_kind("service")) == 1
    assert len(pr.list_by_kind("hook")) == 0
    pr.reset()


def test_register_rejects_bad_plugin():
    from we_together.plugins import plugin_registry as pr
    from we_together.plugins import PluginLoadError
    import pytest
    pr.reset()
    with pytest.raises(PluginLoadError, match="missing attribute: name"):
        pr.register("importer", _BadNoName())
    with pytest.raises(PluginLoadError, match="plugin_api_version"):
        pr.register("importer", _BadWrongVersion())
    with pytest.raises(PluginLoadError, match="provider_kind"):
        pr.register("provider", _BadProviderNoKind())
    with pytest.raises(PluginLoadError, match="event_type"):
        pr.register("hook", _BadHookNoEvent())
    pr.reset()


def test_register_unknown_kind_raises():
    from we_together.plugins import plugin_registry as pr
    import pytest
    with pytest.raises(ValueError, match="unknown plugin kind"):
        pr.register("bogus", _GoodImporter())


def test_get_by_name():
    from we_together.plugins import plugin_registry as pr
    pr.reset()
    pr.register("hook", _GoodHook())
    e = pr.get_by_name("hook", "tick_logger")
    assert e is not None
    assert e.plugin.event_type == "tick.after"
    missing = pr.get_by_name("hook", "not_exist")
    assert missing is None
    pr.reset()


def test_enable_disable_toggle():
    from we_together.plugins import plugin_registry as pr
    pr.reset()
    pr.register("hook", _GoodHook())
    assert len(pr.list_by_kind("hook")) == 1
    assert pr.disable("hook", "tick_logger")
    # 默认不含 disabled
    assert len(pr.list_by_kind("hook")) == 0
    assert len(pr.list_by_kind("hook", include_disabled=True)) == 1
    assert pr.enable("hook", "tick_logger")
    assert len(pr.list_by_kind("hook")) == 1
    pr.reset()


def test_unregister():
    from we_together.plugins import plugin_registry as pr
    pr.reset()
    pr.register("importer", _GoodImporter())
    assert pr.unregister("importer", "good_importer") is True
    assert pr.unregister("importer", "good_importer") is False
    pr.reset()


def test_status_shape():
    from we_together.plugins import plugin_registry as pr
    pr.reset()
    pr.register("service", _GoodService())
    s = pr.status()
    assert s["plugin_api_version"] == "1"
    assert s["total_registered"] == 1
    assert "service" in s["by_kind"]
    assert s["by_kind"]["service"][0]["name"] == "good_service"
    pr.reset()


def test_manual_register_survives_discover():
    """discover 不会清掉 manual 注册的 plugin"""
    from we_together.plugins import plugin_registry as pr
    pr.reset()
    pr.register("importer", _GoodImporter())
    pr.discover(reload=True)
    # manual 保留
    items = pr.list_by_kind("importer")
    names = {e.name for e in items}
    assert "good_importer" in names
    pr.reset()


def test_plugins_list_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "plugins_list.py"
    spec = importlib.util.spec_from_file_location("plugins_list_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)


def test_plugin_api_version_constant():
    from we_together.plugins import PLUGIN_API_VERSION
    assert PLUGIN_API_VERSION == "1"


def test_entry_point_groups_shape():
    from we_together.plugins import ENTRY_POINT_GROUPS
    assert set(ENTRY_POINT_GROUPS.keys()) == {"importer", "service", "provider", "hook"}
    for g in ENTRY_POINT_GROUPS.values():
        assert g.startswith("we_together.")


def test_protocol_runtime_checkable():
    from we_together.plugins import (
        ImporterPlugin, ServicePlugin, ProviderPlugin, HookPlugin,
    )
    assert isinstance(_GoodImporter(), ImporterPlugin)
    assert isinstance(_GoodService(), ServicePlugin)
    assert isinstance(_GoodProvider(), ProviderPlugin)
    assert isinstance(_GoodHook(), HookPlugin)
