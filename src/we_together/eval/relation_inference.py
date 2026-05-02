"""关系推理评估：把当前 db 中的 relations 与 groundtruth 对比。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.eval.groundtruth_loader import GroundtruthSet, load_groundtruth
from we_together.eval.metrics import compute_precision_recall_f1


def _person_name_map(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT person_id, primary_name FROM persons WHERE status = 'active'"
    ).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def _fetch_predicted_relations(db_path: Path) -> set[tuple[str, str, str]]:
    name_map = _person_name_map(db_path)
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """SELECT r.relation_id, r.core_type
           FROM relations r
           WHERE r.status = 'active'"""
    ).fetchall()
    predicted: set[tuple[str, str, str]] = set()
    for rid, core_type in rows:
        participants = conn.execute(
            """SELECT DISTINCT ep.person_id FROM event_participants ep
               JOIN event_targets et ON et.event_id = ep.event_id
               WHERE et.target_type = 'relation' AND et.target_id = ?""",
            (rid,),
        ).fetchall()
        names = sorted([name_map.get(p[0], p[0]) for p in participants])
        if len(names) >= 2:
            predicted.add((names[0], names[1], core_type))
    conn.close()
    return predicted


def evaluate_relation_inference(
    db_path: Path, groundtruth_path: Path,
) -> dict:
    gt: GroundtruthSet = load_groundtruth(groundtruth_path)
    predicted = _fetch_predicted_relations(db_path)
    groundtruth = gt.relation_pairs()

    metrics = compute_precision_recall_f1(predicted, groundtruth)

    return {
        "benchmark": gt.benchmark_name,
        "predicted_count": len(predicted),
        "groundtruth_count": len(groundtruth),
        **metrics,
        "missing_pairs": sorted(groundtruth - predicted),
        "spurious_pairs": sorted(predicted - groundtruth),
    }
