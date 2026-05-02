"""SM-5 Era evolution：长程自演化（N 天模拟），每天跑一轮自激活 + drift + recall。"""
from __future__ import annotations

from pathlib import Path

from we_together.services.memory_recall_service import recall_anniversary_memories
from we_together.services.relation_drift_service import drift_relations
from we_together.services.self_activation_service import (
    self_activate_pair_interactions,
)
from we_together.services.state_decay_service import decay_states


def simulate_era(
    db_path: Path,
    *,
    days: int = 3,
    pair_budget_per_day: int = 1,
) -> dict:
    daily_reports: list[dict] = []
    for day in range(1, days + 1):
        drift = drift_relations(db_path, window_days=30)
        decay = decay_states(db_path, threshold=0.1)

        # 遍历 active scenes 做 pair interaction
        import sqlite3
        conn = sqlite3.connect(db_path)
        scene_ids = [r[0] for r in conn.execute(
            "SELECT scene_id FROM scenes WHERE status = 'active' LIMIT 5"
        ).fetchall()]
        conn.close()

        pair_total = 0
        for sid in scene_ids:
            try:
                r = self_activate_pair_interactions(
                    db_path=db_path, scene_id=sid,
                    daily_budget=pair_budget_per_day, per_run_limit=1,
                )
                pair_total += r.get("created_count", 0)
            except Exception:
                pass

        recall = recall_anniversary_memories(db_path)
        daily_reports.append({
            "day": day,
            "drift_count": drift.get("drifted_count", 0),
            "decay_count": decay.get("decayed_count", 0) if isinstance(decay, dict) else 0,
            "pair_events": pair_total,
            "recall_count": recall.get("recalled_count", 0),
        })
    return {
        "days": days,
        "daily_reports": daily_reports,
        "total_pair_events": sum(r["pair_events"] for r in daily_reports),
        "total_recalls": sum(r["recall_count"] for r in daily_reports),
    }
