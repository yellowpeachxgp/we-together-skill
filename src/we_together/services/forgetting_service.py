"""forgetting_service（Phase 41 FO-1/2/3）：图谱瘦身循环。

职责：
- archive_stale_memories：低 relevance × 久未 access → status=cold
- condense_cluster_candidates：触发 condenser 的候选识别
- slimming_report：图谱瘦身指标

设计原则：
- 只改 status（cold / archived），不物理删除（保留回溯）
- 不变式 #22：archive 与 reactivate 对称（可逆）
- 遗忘曲线：f(days_idle, relevance) → forget_score ∈ [0, 1]
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ForgetParams:
    min_idle_days: int = 30        # 至少 N 天未 access
    max_relevance: float = 0.4      # relevance ≤ 该值才考虑
    limit: int = 100                # 单次最多处理
    dry_run: bool = False


def _forget_score(days_idle: int, relevance: float) -> float:
    """遗忘曲线：Ebbinghaus-like

    days_idle 越久、relevance 越低 → forget_score 越高。
    归一化到 [0, 1]。
    """
    idle_factor = 1.0 - math.exp(-days_idle / 30.0)
    relevance_factor = 1.0 - relevance
    return max(0.0, min(1.0, idle_factor * relevance_factor))


def archive_stale_memories(
    db_path: Path, params: ForgetParams | None = None,
) -> dict:
    params = params or ForgetParams()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    archived: list[dict] = []
    try:
        rows = conn.execute(
            """SELECT memory_id, summary, relevance_score, confidence, updated_at,
               CAST((julianday('now') - julianday(updated_at)) AS INTEGER) AS days_idle
               FROM memories
               WHERE status='active'
                 AND (relevance_score IS NULL OR relevance_score <= ?)
                 AND (julianday('now') - julianday(updated_at)) >= ?
               ORDER BY relevance_score ASC
               LIMIT ?""",
            (params.max_relevance, params.min_idle_days, params.limit),
        ).fetchall()

        for r in rows:
            score = _forget_score(
                days_idle=int(r["days_idle"] or 0),
                relevance=float(r["relevance_score"] or 0.0),
            )
            if score < 0.3:
                continue
            if not params.dry_run:
                conn.execute(
                    "UPDATE memories SET status='cold', updated_at=datetime('now') "
                    "WHERE memory_id=?",
                    (r["memory_id"],),
                )
            archived.append({
                "memory_id": r["memory_id"],
                "relevance": r["relevance_score"],
                "days_idle": r["days_idle"],
                "forget_score": round(score, 3),
            })

        if not params.dry_run:
            conn.commit()
    finally:
        conn.close()

    return {
        "archived_count": len(archived),
        "dry_run": params.dry_run,
        "items": archived,
    }


def reactivate_memory(db_path: Path, memory_id: str) -> bool:
    """对称撤销：把 cold memory 拉回 active（不变式 #22）"""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "UPDATE memories SET status='active', updated_at=datetime('now') "
            "WHERE memory_id=? AND status='cold'",
            (memory_id,),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def condense_cluster_candidates(
    db_path: Path, *, min_cluster_size: int = 5, idle_days: int = 60,
) -> list[dict]:
    """识别可 condenser 的 memory 簇：同 person 下 N 条相似 + idle。
    不真调 condenser，只返回 candidate 列表；由调用方决定是否触发。
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT mo.owner_id AS person_id, COUNT(*) AS cnt
               FROM memories m
               JOIN memory_owners mo ON mo.memory_id=m.memory_id
               WHERE m.status='active'
                 AND mo.owner_type='person'
                 AND (julianday('now') - julianday(m.updated_at)) >= ?
               GROUP BY mo.owner_id
               HAVING cnt >= ?""",
            (idle_days, min_cluster_size),
        ).fetchall()
        return [{"person_id": r["person_id"], "memory_count": r["cnt"]} for r in rows]
    finally:
        conn.close()


def slimming_report(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            """SELECT
               (SELECT COUNT(*) FROM memories WHERE status='active'),
               (SELECT COUNT(*) FROM memories WHERE status='cold'),
               (SELECT COUNT(*) FROM memories WHERE status='archived'),
               (SELECT COUNT(*) FROM memories)""",
        ).fetchone()
    finally:
        conn.close()
    total = row[3] or 1
    return {
        "active": row[0], "cold": row[1], "archived": row[2], "total": row[3],
        "active_ratio": round(row[0] / total, 3),
        "cold_ratio": round(row[1] / total, 3),
    }
