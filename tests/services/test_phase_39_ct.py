"""Phase 39 — Tick 真运行 + 归档 (CT slices)。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _seed(root: Path) -> Path:
    from seed_demo import seed_society_c
    seed_society_c(root)
    return root / "db" / "main.sqlite3"


def test_tick_cost_tracker_basic():
    from we_together.services.tick_cost_tracker import TickCostTracker
    t = TickCostTracker()
    t.track("mock", prompt_tokens=10, completion_tokens=5)
    t.track("mock", prompt_tokens=20, completion_tokens=8)
    t.track("anthropic", prompt_tokens=100, completion_tokens=200)
    s = t.summary()
    assert s["total_calls"] == 3
    assert s["total_tokens"] == 10 + 5 + 20 + 8 + 100 + 200
    assert s["by_provider"]["mock"]["calls"] == 2
    assert s["by_provider"]["anthropic"]["calls"] == 1


def test_tick_cost_tracker_estimated():
    from we_together.services.tick_cost_tracker import TickCostTracker
    t = TickCostTracker()
    t.track_estimated("mock", text_in="hello world" * 100, text_out="reply")
    s = t.summary()
    assert s["total_calls"] == 1
    assert s["by_provider"]["mock"]["prompt_tokens"] > 0


def test_tick_cost_tracker_reset():
    from we_together.services.tick_cost_tracker import TickCostTracker
    t = TickCostTracker()
    t.track("mock", prompt_tokens=1, completion_tokens=1)
    t.reset()
    assert t.summary()["total_calls"] == 0


def test_simulate_week_build_report(temp_project_dir):
    db = _seed(temp_project_dir)
    import importlib.util
    p = REPO_ROOT / "scripts" / "simulate_week.py"
    spec = importlib.util.spec_from_file_location("sim_week_2", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.build_report(db, ticks=2, budget=0)
    assert report["ticks"] == 2
    assert "sanity" in report
    assert "meta" in report
    assert report["meta"]["ticks"] == 2


def test_simulate_week_archive(temp_project_dir):
    db = _seed(temp_project_dir)
    import importlib.util
    p = REPO_ROOT / "scripts" / "simulate_week.py"
    spec = importlib.util.spec_from_file_location("sim_week_3", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    bench_dir = temp_project_dir / "benchmarks" / "tick_runs"
    report = mod.build_report(db, ticks=1, budget=0)
    path = mod.archive(report, bench_dir)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["ticks"] == 1


def test_simulate_writes_real_snapshots(temp_project_dir):
    """Phase 38 修复 time_simulator 后，snapshot_id 真被写入"""
    db = _seed(temp_project_dir)
    from we_together.services.time_simulator import simulate, TickBudget
    r = simulate(db, ticks=3, budget=TickBudget(llm_calls=0))
    # 修复后至少一个 snapshot_id 非 None
    non_null = [s for s in r["snapshot_ids"] if s]
    assert len(non_null) >= 1
    import sqlite3
    conn = sqlite3.connect(db)
    cnt = conn.execute(
        "SELECT COUNT(*) FROM snapshots WHERE snapshot_id LIKE 'snap_tick_%'"
    ).fetchone()[0]
    conn.close()
    assert cnt >= 1


def test_long_run_30_ticks_stable(temp_project_dir):
    """30 次 tick 无 LLM 预算，图谱不应崩坏"""
    db = _seed(temp_project_dir)
    from we_together.services.time_simulator import simulate, TickBudget
    from we_together.services.tick_sanity import evaluate
    r = simulate(db, ticks=30, budget=TickBudget(llm_calls=0))
    assert r["ticks"] == 30
    sanity = evaluate(db, ticks=30)
    assert sanity["healthy"] is True
    # 异常总数仍在可控范围
    assert sanity["anomalies"]["anomaly_count"] < 50


def test_rollback_tick_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "rollback_tick.py"
    spec = importlib.util.spec_from_file_location("rb_tick_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)


def test_tick_scheduling_doc():
    p = REPO_ROOT / "docs" / "tick-scheduling.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "crontab" in text
    assert "CronJob" in text or "NATS" in text


def test_archive_benchmark_file_layout(temp_project_dir):
    db = _seed(temp_project_dir)
    import importlib.util
    p = REPO_ROOT / "scripts" / "simulate_week.py"
    spec = importlib.util.spec_from_file_location("sim_week_4", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    report = mod.build_report(db, ticks=1, budget=0)
    bench_dir = temp_project_dir / "benchmarks" / "tick_runs"
    path = mod.archive(report, bench_dir)
    # 命名是 ISO timestamp 式
    assert path.suffix == ".json"
    assert len(path.stem) >= 15  # YYYY-MM-DDTHH-MM-SSZ 至少 20+
    assert "Z" in path.stem
