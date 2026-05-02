"""time_simulator（Phase 34 EV）：把 state_decay / relation_drift / proactive_scan /
self_activation 编排到一次"图谱时钟 tick"里。

不变式 #20：tick 写入必须能在无人工干预下被 snapshot 回滚至任一时间点（闭环可逆）。
实现方式：每个 tick 结束调 snapshot_service，把 tick 视为一次 patch 批的提交边界。
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable


@dataclass
class TickResult:
    tick_index: int
    started_at: str
    ended_at: str
    decay: dict = field(default_factory=dict)
    drift: dict = field(default_factory=dict)
    proactive: dict = field(default_factory=dict)
    self_activation: dict = field(default_factory=dict)
    snapshot_id: str | None = None
    budget_exhausted: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "tick_index": self.tick_index,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "decay": dict(self.decay),
            "drift": dict(self.drift),
            "proactive": dict(self.proactive),
            "self_activation": dict(self.self_activation),
            "snapshot_id": self.snapshot_id,
            "budget_exhausted": self.budget_exhausted,
            "notes": list(self.notes),
        }


@dataclass
class TickBudget:
    llm_calls: int = 10
    proactive_daily: int = 3
    drift_limit: int = 200
    decay_limit: int = 500

    def consume_llm(self, n: int = 1) -> bool:
        if self.llm_calls <= 0:
            return False
        self.llm_calls -= n
        return True


# hooks registry
_HOOKS_BEFORE: list[Callable[[int, Path], None]] = []
_HOOKS_AFTER: list[Callable[[TickResult, Path], None]] = []


def register_before_hook(fn: Callable[[int, Path], None]) -> None:
    _HOOKS_BEFORE.append(fn)


def register_after_hook(fn: Callable[[TickResult, Path], None]) -> None:
    _HOOKS_AFTER.append(fn)


def clear_hooks() -> None:
    _HOOKS_BEFORE.clear()
    _HOOKS_AFTER.clear()


def _make_snapshot_after_tick(db_path: Path, tick_index: int) -> str | None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        snap_id = f"snap_tick_{tick_index}_{int(datetime.now(UTC).timestamp())}"
        conn.execute(
            """INSERT INTO snapshots(snapshot_id, based_on_snapshot_id,
               trigger_event_id, summary, graph_hash, created_at)
               VALUES(?, NULL, NULL, ?, NULL, datetime('now'))""",
            (snap_id, f"tick {tick_index} auto-snapshot"),
        )
        conn.commit()
        return snap_id
    except Exception:
        return None
    finally:
        conn.close()


def run_tick(
    db_path: Path, *,
    tick_index: int = 0,
    budget: TickBudget | None = None,
    llm_client=None,
    do_decay: bool = True,
    do_drift: bool = True,
    do_proactive: bool = True,
    do_self_activation: bool = False,
    make_snapshot: bool = True,
) -> TickResult:
    budget = budget or TickBudget()
    started = datetime.now(UTC).isoformat()
    for hk in list(_HOOKS_BEFORE):
        try:
            hk(tick_index, db_path)
        except Exception:
            pass

    result = TickResult(tick_index=tick_index, started_at=started, ended_at="")

    if do_decay:
        try:
            from we_together.services.state_decay_service import decay_states
            result.decay = decay_states(db_path, limit=budget.decay_limit)
        except Exception as exc:
            result.notes.append(f"decay_error: {exc}")

    if do_drift:
        try:
            from we_together.services.relation_drift_service import drift_relations
            result.drift = drift_relations(db_path, limit=budget.drift_limit)
        except Exception as exc:
            result.notes.append(f"drift_error: {exc}")

    if do_proactive:
        if budget.consume_llm():
            try:
                from we_together.services.proactive_agent import proactive_scan
                result.proactive = proactive_scan(
                    db_path, daily_budget=budget.proactive_daily,
                    llm_client=llm_client,
                )
            except Exception as exc:
                result.notes.append(f"proactive_error: {exc}")
        else:
            result.budget_exhausted = True
            result.notes.append("proactive_skipped_budget")

    if do_self_activation:
        if budget.consume_llm():
            try:
                from we_together.services.self_activation_service import self_activate
                result.self_activation = self_activate(
                    db_path, llm_client=llm_client,
                ) if llm_client else {}
            except Exception as exc:
                result.notes.append(f"self_activate_error: {exc}")
        else:
            result.budget_exhausted = True

    if make_snapshot:
        result.snapshot_id = _make_snapshot_after_tick(db_path, tick_index)

    result.ended_at = datetime.now(UTC).isoformat()

    for hk in list(_HOOKS_AFTER):
        try:
            hk(result, db_path)
        except Exception:
            pass

    return result


def simulate(
    db_path: Path, *,
    ticks: int = 7,
    budget: TickBudget | None = None,
    llm_client=None,
    do_self_activation: bool = False,
) -> dict:
    """连续跑 N 次 tick，返回总结。"""
    budget = budget or TickBudget()
    history: list[TickResult] = []
    for i in range(ticks):
        r = run_tick(
            db_path, tick_index=i, budget=budget, llm_client=llm_client,
            do_self_activation=do_self_activation,
        )
        history.append(r)

    return {
        "ticks": ticks,
        "history": [r.to_dict() for r in history],
        "llm_calls_remaining": budget.llm_calls,
        "snapshot_ids": [r.snapshot_id for r in history if r.snapshot_id],
    }


def rollback_to_tick(db_path: Path, snapshot_id: str) -> dict:
    """回滚到特定 tick 的 snapshot（复用 snapshot_service）。"""
    from we_together.services.snapshot_service import rollback_to_snapshot
    return rollback_to_snapshot(db_path, snapshot_id=snapshot_id)
