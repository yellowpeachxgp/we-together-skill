"""Phase 60 — 反身能力 (RX slices)。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def test_list_adrs_returns_60_plus():
    from we_together.services.self_introspection import list_adrs
    adrs = list_adrs()
    assert len(adrs) >= 60
    first = adrs[0]
    assert first["adr_id"].startswith("ADR ")
    assert first["title"]
    assert first["status"]


def test_adr_status_parsed():
    from we_together.services.self_introspection import list_adrs
    adrs = list_adrs()
    statuses = {a["status"].lower() for a in adrs}
    # 至少有 accepted
    assert "accepted" in statuses or any("accept" in s for s in statuses)


def test_list_invariants_28():
    from we_together.services.self_introspection import list_invariants
    invs = list_invariants()
    assert len(invs) >= 28


def test_invariant_coverage_100():
    from we_together.services.self_introspection import invariant_coverage
    cov = invariant_coverage()
    assert cov["coverage_ratio"] == 1.0


def test_check_invariant_valid():
    from we_together.services.self_introspection import check_invariant
    r = check_invariant(26)
    assert r["found"] is True
    assert r["covered"] is True
    assert "时间范围" in r["title"] or "时间" in r["description"]


def test_check_invariant_missing():
    from we_together.services.self_introspection import check_invariant
    r = check_invariant(999)
    assert r["found"] is False


def test_list_services_ge_60():
    from we_together.services.self_introspection import list_services
    svcs = list_services()
    assert len(svcs) >= 60


def test_list_migrations_21_plus():
    from we_together.services.self_introspection import list_migrations
    ms = list_migrations()
    assert len(ms) >= 21
    assert ms[0]["migration_id"] == "0001"


def test_list_scripts_ge_30():
    from we_together.services.self_introspection import list_scripts
    ss = list_scripts()
    assert len(ss) >= 30


def test_list_plugins_has_registry():
    from we_together.services.self_introspection import list_plugins
    r = list_plugins()
    assert "plugin_api_version" in r or "by_kind" in r


def test_self_describe_complete():
    from we_together.services.self_introspection import self_describe
    d = self_describe()
    assert d["name"] == "we-together"
    assert d["adrs_total"] >= 60
    assert d["invariants_total"] >= 28
    assert d["services_total"] >= 60
    assert d["migrations_total"] >= 21
    assert d["invariants_coverage_ratio"] == 1.0
    assert "A_strict_engineering" in d["pillars"]


def test_mcp_tools_have_self_describe():
    from we_together.runtime.adapters.mcp_adapter import build_mcp_tools
    tools = build_mcp_tools()
    names = {t["name"] for t in tools}
    assert "we_together_self_describe" in names
    assert "we_together_list_invariants" in names
    assert "we_together_check_invariant" in names


def test_self_audit_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "self_audit.py"
    spec = importlib.util.spec_from_file_location("self_audit_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)


def test_adr_file_references_exist():
    """list_adrs 返回的 file 字段必须真实存在"""
    from we_together.services.self_introspection import list_adrs
    for a in list_adrs()[:5]:
        p = REPO_ROOT / a["file"]
        assert p.exists(), f"ADR file missing: {a['file']}"


def test_migration_files_exist():
    from we_together.services.self_introspection import list_migrations
    for m in list_migrations():
        p = REPO_ROOT / m["file"]
        assert p.exists()
