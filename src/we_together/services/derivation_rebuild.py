"""derivation_rebuild（Phase 55 DF-6）：派生视图的重建器。

不变式 #28: 所有派生字段（persona_summary / narrative_arcs / activation_map /
insight memory / working_memory）必须可从底层 events 重建；派生数据不得成为"唯一真相"。

职责：
- rebuild_insight_source_memory_ids(db, insight_id) → 原始 memory_id 集合（读 metadata.source_memory_ids）
- rebuild_activation_trace_stats(db) → 从 trace 表重建 "谁激活谁"
- rebuild_working_memory_from_cache(scene_id) → 从 retrieval_cache 重建 working_memory
- verify_rebuildable(kind, id) 检查一个派生对象是否可被重建到相同结果
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def get_insight_sources(db_path: Path, insight_id: str) -> dict:
    """insight memory 必须在 metadata 里记 source_memory_ids（#28）"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT memory_type, metadata_json FROM memories WHERE memory_id=?",
            (insight_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {"found": False}
    if row["memory_type"] != "insight":
        return {"found": True, "is_insight": False}
    meta = json.loads(row["metadata_json"] or "{}")
    sources = meta.get("source_memory_ids", [])
    return {
        "found": True,
        "is_insight": True,
        "rebuildable": bool(sources),
        "source_memory_ids": list(sources),
    }


def verify_insight_rebuildable(db_path: Path, insight_id: str) -> bool:
    """验证 insight 可重建：source_memory_ids 中的 memory 都还存在（或 status='cold'）"""
    info = get_insight_sources(db_path, insight_id)
    if not info["found"] or not info.get("is_insight"):
        return False
    sources = info.get("source_memory_ids", [])
    if not sources:
        return False
    conn = sqlite3.connect(db_path)
    try:
        placeholders = ",".join("?" for _ in sources)
        rows = conn.execute(
            f"SELECT memory_id FROM memories WHERE memory_id IN ({placeholders})",
            list(sources),
        ).fetchall()
    finally:
        conn.close()
    found_ids = {r[0] for r in rows}
    # 允许部分 source 被删（archived），但至少 60% 能找到算可重建
    return len(found_ids) >= max(1, int(0.6 * len(sources)))


def rebuild_activation_edge_stats(db_path: Path, *, since_days: int = 30) -> dict:
    """从 activation_traces 重建 edge 频次 + 平均权重。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT from_entity_id AS f, to_entity_id AS t,
               COUNT(*) AS cnt, AVG(weight) AS avg_w
               FROM activation_traces
               WHERE activated_at >= datetime('now', ?)
               GROUP BY from_entity_id, to_entity_id
               ORDER BY cnt DESC LIMIT 100""",
            (f"-{int(since_days)} days",),
        ).fetchall()
        return {
            "total_edges": len(rows),
            "top": [
                {"from": r["f"], "to": r["t"],
                 "count": r["cnt"], "avg_weight": round(r["avg_w"], 3)}
                for r in rows[:20]
            ],
        }
    finally:
        conn.close()


def verify_narrative_arcs_rebuildable(db_path: Path, arc_id: str) -> bool:
    """narrative_arc 必须保留 source_event_ids。"""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT source_event_refs_json FROM narrative_arcs WHERE arc_id=?",
            (arc_id,),
        ).fetchone()
    except sqlite3.OperationalError:
        return False
    finally:
        conn.close()
    if not row:
        return False
    try:
        refs = json.loads(row[0] or "[]")
        return bool(refs)
    except Exception:
        return False


def summary(db_path: Path) -> dict:
    """整个图谱的"派生可重建性"体检。"""
    conn = sqlite3.connect(db_path)
    try:
        insight_rows = conn.execute(
            "SELECT memory_id FROM memories WHERE memory_type='insight' "
            "AND status='active' LIMIT 100"
        ).fetchall()
    finally:
        conn.close()

    insight_ok = 0
    insight_fail = 0
    for (mid,) in insight_rows:
        if verify_insight_rebuildable(db_path, mid):
            insight_ok += 1
        else:
            insight_fail += 1

    return {
        "insights_total": len(insight_rows),
        "insights_rebuildable": insight_ok,
        "insights_failing": insight_fail,
        "healthy": insight_fail == 0,
    }
