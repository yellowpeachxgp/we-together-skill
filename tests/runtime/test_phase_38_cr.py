"""Phase 38 — 消费就绪 (CR slices)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def test_getting_started_doc_exists():
    p = REPO_ROOT / "docs" / "getting-started.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "bootstrap" in text
    assert "mcp_server" in text


def test_host_docs_exist():
    for host in ["claude-desktop", "claude-code", "openai-assistants"]:
        p = REPO_ROOT / "docs" / "hosts" / f"{host}.md"
        assert p.exists(), f"missing host doc: {host}"


def test_dashboard_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "dashboard.py"
    spec = importlib.util.spec_from_file_location("wt_dashboard", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert callable(m._summary)
    assert callable(m._recent_ticks)
    assert "we-together" in m.DASHBOARD_HTML


def test_dashboard_summary_works(temp_project_with_migrations):
    import importlib.util

    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    p = REPO_ROOT / "scripts" / "dashboard.py"
    spec = importlib.util.spec_from_file_location("wt_dashboard2", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    s = m._summary(temp_project_with_migrations)
    assert "persons" in s
    assert isinstance(s["persons"], int)
    assert s["tenant_id"] == "default"
    t = m._recent_ticks(temp_project_with_migrations)
    assert "ticks" in t


def test_dashboard_summary_works_for_tenant_root(tmp_path):
    import importlib.util
    import sqlite3

    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.tenant_router import resolve_tenant_root

    root = tmp_path / "proj"
    tenant_root = resolve_tenant_root(root, "alpha")
    bootstrap_project(tenant_root)

    conn = sqlite3.connect(tenant_root / "db" / "main.sqlite3")
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_dash_t', 'Tenant Dash', 'active', 0.9, '{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    p = REPO_ROOT / "scripts" / "dashboard.py"
    spec = importlib.util.spec_from_file_location("wt_dashboard_tenant", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    s = m._summary(tenant_root)
    assert s["persons"] >= 1
    assert s["tenant_id"] == "alpha"


def test_skill_host_smoke_all_steps(tmp_path):
    import importlib.util
    p = REPO_ROOT / "scripts" / "skill_host_smoke.py"
    spec = importlib.util.spec_from_file_location("wt_smoke", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    report = m.run_smoke(tmp_path)
    steps = {r["step"]: r["ok"] for r in report["results"]}
    run_turn = next(r for r in report["results"] if r["step"] == "run_turn")
    assert steps.get("bootstrap") is True
    assert steps.get("seed_society_c") is True
    assert steps.get("run_turn") is True
    assert run_turn["text"] == "你好，我收到了。"
    assert steps.get("dashboard_summary") is True


def test_skill_host_smoke_tenant_root(tmp_path):
    import importlib.util

    from we_together.services.tenant_router import resolve_tenant_root

    p = REPO_ROOT / "scripts" / "skill_host_smoke.py"
    spec = importlib.util.spec_from_file_location("wt_smoke_tenant", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    report = m.run_smoke(resolve_tenant_root(tmp_path, "alpha"))
    steps = {r["step"]: r["ok"] for r in report["results"]}
    run_turn = next(r for r in report["results"] if r["step"] == "run_turn")
    assert steps.get("bootstrap") is True
    assert steps.get("seed_society_c") is True
    assert steps.get("run_turn") is True
    assert run_turn["text"] == "你好，我收到了。"
    assert steps.get("dashboard_summary") is True


def test_metrics_endpoint_prometheus_format():
    from we_together.observability.metrics import (
        counter_inc,
        export_prometheus_text,
        reset,
    )
    reset()
    counter_inc("we_together_tick_total", 1.0, {"phase": "test"})
    text = export_prometheus_text()
    assert "we_together_tick_total" in text
    reset()


def test_mcp_adapter_tool_count_post_phase33():
    """Phase 38 验收：Phase 33 已把 tools 扩展到 6 个"""
    from we_together.runtime.adapters.mcp_adapter import (
        build_mcp_prompts,
        build_mcp_resources,
        build_mcp_tools,
    )
    # Phase 60 新增 3 个 self-introspection 工具 → 9
    assert len(build_mcp_tools()) >= 6
    assert len(build_mcp_resources()) == 2
    assert len(build_mcp_prompts()) == 1


def test_skill_schema_is_still_v1():
    """Phase 38 新增功能不能破坏 schema v1（ADR 0034 不变式 #19）"""
    from we_together.runtime.skill_runtime import SKILL_SCHEMA_VERSION
    assert SKILL_SCHEMA_VERSION == "1"
