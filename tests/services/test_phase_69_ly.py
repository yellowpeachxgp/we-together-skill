from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from seed_demo import seed_society_c

import we_together.services.proactive_agent as proactive_agent
from we_together.llm import LLMMessage, LLMResponse
from we_together.llm.audited_client import UsageAuditedLLMClient, estimate_cost_usd
from we_together.llm.providers.mock import MockLLMClient


def _load_year_module():
    p = REPO_ROOT / "scripts" / "simulate_year.py"
    spec = importlib.util.spec_from_file_location("sim_year_phase_69", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _UsageBaseClient:
    provider = "unit-test"

    def chat(self, messages, **kwargs):
        return LLMResponse(
            content="ok",
            model="unit-test-model",
            usage={"prompt_tokens": 11, "completion_tokens": 7},
            raw={},
        )

    def chat_json(self, messages, schema_hint, **kwargs):
        return {"ok": True}


def test_usage_audited_client_tracks_real_usage():
    client = UsageAuditedLLMClient(_UsageBaseClient())
    resp = client.chat([LLMMessage(role="user", content="hello")])
    assert resp.content == "ok"
    summary = client.summary()
    assert summary["total_calls"] == 1
    assert summary["total_tokens"] == 18
    assert summary["by_provider"]["unit-test"]["prompt_tokens"] == 11


def test_usage_audited_client_estimates_chat_json():
    client = UsageAuditedLLMClient(MockLLMClient(default_json={"action": "check_in"}))
    payload = client.chat_json(
        [LLMMessage(role="user", content="please return json")],
        schema_hint={"action": "str"},
    )
    assert payload["action"] == "check_in"
    summary = client.summary()
    assert summary["total_calls"] == 1
    assert summary["total_tokens"] > 0


def test_estimate_cost_usd():
    usage = {
        "by_provider": {
            "mock": {"prompt_tokens": 1000, "completion_tokens": 500, "calls": 3}
        }
    }
    assert estimate_cost_usd(
        usage,
        prompt_price_per_1k=0.01,
        completion_price_per_1k=0.02,
    ) == 0.02


def test_simulate_year_dry_run_provider_check(monkeypatch, capsys):
    mod = _load_year_module()

    class _Client:
        provider = "mock"
        model = "mock-model"

    monkeypatch.setattr(mod, "get_llm_client", lambda provider=None: _Client())
    monkeypatch.setattr(
        "sys.argv",
        ["simulate_year.py", "--dry-run-provider-check", "--provider", "mock"],
    )
    rc = mod.main()
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ready"] is True
    assert out["provider"] == "mock"


def test_run_year_reports_llm_usage(temp_project_dir, monkeypatch):
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"

    trigger = proactive_agent.Trigger(
        name="silence",
        target_person_id=next(iter(seed_society_c(temp_project_dir)["persons"].values())),
        reason="forced test trigger",
    )
    monkeypatch.setattr(proactive_agent, "scan_all_triggers", lambda db_path: [trigger])
    monkeypatch.setattr(proactive_agent, "check_budget", lambda db_path, daily_budget=5: 1)

    mod = _load_year_module()
    llm = MockLLMClient(
        default_json={"action": "check_in", "text": "你好", "confidence": 0.8}
    )
    report = mod.run_year(
        db,
        days=1,
        budget=1,
        llm_client=llm,
        prompt_price_per_1k=0.01,
        completion_price_per_1k=0.02,
    )
    assert report["llm_provider"] == "mock"
    assert report["llm_usage"]["total_calls"] >= 1
    assert report["estimated_cost_usd"] >= 0.0


def test_run_year_monthly_usage_breakdown(temp_project_dir, monkeypatch):
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"

    person_ids = list(seed_society_c(temp_project_dir)["persons"].values())
    monkeypatch.setattr(
        proactive_agent,
        "scan_all_triggers",
        lambda db_path: [
            proactive_agent.Trigger(
                name="silence",
                target_person_id=person_ids[0],
                reason="month-0",
            ),
            proactive_agent.Trigger(
                name="silence",
                target_person_id=person_ids[1],
                reason="month-1",
            ),
        ],
    )
    monkeypatch.setattr(proactive_agent, "check_budget", lambda db_path, daily_budget=5: 2)

    mod = _load_year_module()
    llm = MockLLMClient(
        default_json={"action": "check_in", "text": "你好", "confidence": 0.8}
    )
    report = mod.run_year(
        db,
        days=31,
        budget=31,
        llm_client=llm,
        prompt_price_per_1k=0.01,
        completion_price_per_1k=0.02,
    )
    assert report["total_months"] == 2
    assert report["monthly"][0]["days"] == 30
    assert report["monthly"][1]["days"] == 1
    assert "llm_usage" in report["monthly"][0]
    assert report["monthly"][0]["llm_usage"]["total_calls"] >= 1


def test_run_year_monthly_report_dir_writes_files(temp_project_dir, monkeypatch):
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    monthly_dir = temp_project_dir / "benchmarks" / "year_runs" / "monthly"

    monkeypatch.setattr(proactive_agent, "scan_all_triggers", lambda db_path: [])

    mod = _load_year_module()
    report = mod.run_year(
        db,
        days=31,
        budget=0,
        monthly_report_dir=monthly_dir,
    )
    assert report["monthly_report_dir"]
    files = sorted(monthly_dir.glob("year_month_*.json"))
    assert len(files) == 2
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert "month" in payload
    assert "llm_usage" in payload
