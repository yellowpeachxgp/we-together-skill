"""Phase 59 — 年度真跑 (SY slices)。"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _load_year_module():
    p = REPO_ROOT / "scripts" / "simulate_year.py"
    spec = importlib.util.spec_from_file_location("sim_year_m", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_month_index():
    m = _load_year_module()
    assert m._month_index(0) == 0
    assert m._month_index(29) == 0
    assert m._month_index(30) == 1
    assert m._month_index(365) == 12


def test_run_year_3_days(temp_project_dir):
    """最小路径: 3 天跑通"""
    from seed_demo import seed_society_c
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"

    m = _load_year_module()
    r = m.run_year(db, days=3, budget=0)
    assert r["days"] == 3
    assert r["total_months"] == 1


def test_run_year_30_days_single_month(temp_project_dir):
    from seed_demo import seed_society_c
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"

    m = _load_year_module()
    r = m.run_year(db, days=30, budget=0)
    assert r["total_months"] == 1
    assert r["monthly"][0]["days"] == 30


def test_run_year_90_days_three_months(temp_project_dir):
    from seed_demo import seed_society_c
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"

    m = _load_year_module()
    r = m.run_year(db, days=90, budget=0)
    assert r["total_months"] == 3
    assert sum(mo["days"] for mo in r["monthly"]) == 90


def test_run_year_archive_monthly(temp_project_dir):
    from seed_demo import seed_society_c
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    archive_dir = temp_project_dir / "benchmarks" / "year_runs"

    m = _load_year_module()
    r = m.run_year(db, days=10, budget=0, archive_dir=archive_dir)
    assert r["archived_to"]

    archived_files = list(archive_dir.glob("year_run_*.json"))
    assert len(archived_files) == 1
    payload = json.loads(archived_files[0].read_text(encoding="utf-8"))
    assert payload["days"] == 10


def test_run_year_preserves_integrity(temp_project_dir):
    """跑 60 天后 integrity 必须 healthy"""
    from seed_demo import seed_society_c
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"

    m = _load_year_module()
    r = m.run_year(db, days=60, budget=0)
    assert r["integrity"]["healthy"] is True


def test_run_year_no_llm_budget_stable(temp_project_dir):
    """budget=0 跑 30 天，不崩 + budget_remaining=0"""
    from seed_demo import seed_society_c
    seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"

    m = _load_year_module()
    r = m.run_year(db, days=30, budget=0)
    assert r["budget_remaining"] == 0


def test_archived_year_run_in_repo():
    """仓库里有真跑过的 365 天报告（P59 真归档）"""
    archive_dir = REPO_ROOT / "benchmarks" / "year_runs"
    if not archive_dir.exists():
        import pytest
        pytest.skip("year_runs 目录尚未归档（第一次跑）")

    files = list(archive_dir.glob("year_run_*.json"))
    if not files:
        import pytest
        pytest.skip("还没归档")

    # 读第一个报告，校验格式
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["days"] >= 1
    assert payload["sanity"]["healthy"] is True
    assert payload["integrity"]["healthy"] is True
