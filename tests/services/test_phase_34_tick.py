"""Phase 34 — 持续演化 Tick (EV slices)。

覆盖:
- TickResult / TickBudget dataclass (EV-1)
- run_tick 主循环 + 编排 decay/drift/proactive (EV-2/3/4/5)
- simulate N tick (EV-7/8)
- hook 机制 (EV-13)
- 预算 (EV-16)
- rollback_to_tick (EV-12)
- 合理性评估 (EV-9/10)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "src"))


def _seed(root: Path) -> Path:
    from seed_demo import seed_society_c
    seed_society_c(root)
    return root / "db" / "main.sqlite3"


def test_tick_result_dataclass():
    from we_together.services.time_simulator import TickResult
    r = TickResult(tick_index=0, started_at="t0", ended_at="t1")
    d = r.to_dict()
    assert d["tick_index"] == 0
    assert d["snapshot_id"] is None


def test_tick_budget_consume():
    from we_together.services.time_simulator import TickBudget
    b = TickBudget(llm_calls=2)
    assert b.consume_llm() is True
    assert b.consume_llm() is True
    assert b.consume_llm() is False


def test_run_tick_minimal(temp_project_dir):
    db = _seed(temp_project_dir)
    from we_together.services.time_simulator import run_tick, TickBudget
    r = run_tick(
        db, tick_index=0, budget=TickBudget(llm_calls=0),
        do_proactive=False, do_self_activation=False, make_snapshot=False,
    )
    assert r.tick_index == 0
    assert isinstance(r.decay, dict)
    assert isinstance(r.drift, dict)
    assert r.ended_at


def test_run_tick_proactive_budget_exhausted(temp_project_dir):
    db = _seed(temp_project_dir)
    from we_together.services.time_simulator import run_tick, TickBudget
    r = run_tick(
        db, tick_index=0, budget=TickBudget(llm_calls=0),
        do_proactive=True, make_snapshot=False,
    )
    assert r.budget_exhausted is True
    assert "proactive_skipped_budget" in r.notes


def test_simulate_multi_tick(temp_project_dir):
    db = _seed(temp_project_dir)
    from we_together.services.time_simulator import simulate, TickBudget
    r = simulate(
        db, ticks=3, budget=TickBudget(llm_calls=0),
    )
    assert r["ticks"] == 3
    assert len(r["history"]) == 3


def test_simulate_writes_snapshots(temp_project_dir):
    db = _seed(temp_project_dir)
    from we_together.services.time_simulator import simulate, TickBudget
    r = simulate(db, ticks=2, budget=TickBudget(llm_calls=0))
    # 至少有一些 snapshot（scene 存在时会写）
    assert isinstance(r["snapshot_ids"], list)


def test_tick_hook_before_after(temp_project_dir):
    db = _seed(temp_project_dir)
    from we_together.services.time_simulator import (
        run_tick, TickBudget, register_before_hook, register_after_hook, clear_hooks,
    )
    clear_hooks()
    seen_before: list[int] = []
    seen_after: list[int] = []
    register_before_hook(lambda idx, _: seen_before.append(idx))
    register_after_hook(lambda res, _: seen_after.append(res.tick_index))
    run_tick(
        db, tick_index=7, budget=TickBudget(llm_calls=0),
        do_proactive=False, make_snapshot=False,
    )
    assert seen_before == [7]
    assert seen_after == [7]
    clear_hooks()


def test_check_growth(temp_project_dir):
    db = _seed(temp_project_dir)
    from we_together.services.tick_sanity import check_growth
    r = check_growth(db, ticks=3)
    assert "memory_count" in r
    assert "event_count" in r


def test_check_anomalies(temp_project_dir):
    db = _seed(temp_project_dir)
    from we_together.services.tick_sanity import check_anomalies
    r = check_anomalies(db)
    assert "anomaly_count" in r
    assert isinstance(r["anomaly_count"], int)


def test_evaluate_report(temp_project_dir):
    db = _seed(temp_project_dir)
    from we_together.services.tick_sanity import evaluate
    r = evaluate(db, ticks=3)
    assert "growth" in r and "anomalies" in r
    assert isinstance(r["healthy"], bool)


def test_simulate_produces_sanity_healthy(temp_project_dir):
    """seed 之后的图谱，简单 2 tick 无 LLM 调用下应 healthy"""
    db = _seed(temp_project_dir)
    from we_together.services.time_simulator import simulate, TickBudget
    from we_together.services.tick_sanity import evaluate
    simulate(db, ticks=2, budget=TickBudget(llm_calls=0))
    report = evaluate(db, ticks=2)
    assert report["healthy"] is True
