"""dream_cycle + insight（Phase 52 AG-4/5/6/7/8）：agent 的"睡眠期"整理。

职责：
- 压缩近期 memory（高 relevance 保留，低 relevance → archive）
- 发现跨 memory 关联 → 生成 `insight` 类型的新 memory
- 调整 persona_facets（learning）
- 不真调 LLM（Mock）；真 LLM 留给 simulate_year 真跑

不变式 #28（Phase 55 正式）：派生 insight 必须可重建（保留 source_memory_ids）
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InsightSeed:
    summary: str
    source_memory_ids: list[str]
    confidence: float = 0.6


def _find_co_themed_memory_clusters(
    db_path: Path, *, min_cluster_size: int = 3, lookback_days: int = 30,
) -> list[list[str]]:
    """极简：按 owner_id 聚类近期 memory，N 条以上视为一簇。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    clusters: dict[str, list[str]] = {}
    try:
        rows = conn.execute(
            """SELECT mo.owner_id, m.memory_id FROM memories m
               JOIN memory_owners mo ON mo.memory_id=m.memory_id
               WHERE m.status='active' AND mo.owner_type='person'
                 AND m.updated_at >= datetime('now', ?)
               ORDER BY mo.owner_id""",
            (f"-{int(lookback_days)} days",),
        ).fetchall()
    finally:
        conn.close()
    for r in rows:
        clusters.setdefault(r["owner_id"], []).append(r["memory_id"])
    return [c for c in clusters.values() if len(c) >= min_cluster_size]


def generate_insights(
    db_path: Path, *, min_cluster_size: int = 3, lookback_days: int = 30,
) -> list[InsightSeed]:
    clusters = _find_co_themed_memory_clusters(
        db_path, min_cluster_size=min_cluster_size, lookback_days=lookback_days,
    )
    out: list[InsightSeed] = []
    for cluster in clusters:
        out.append(InsightSeed(
            summary=f"[insight] 累计 {len(cluster)} 条相关记忆形成一个主题",
            source_memory_ids=list(cluster),
            confidence=min(0.9, 0.5 + 0.05 * len(cluster)),
        ))
    return out


def persist_insight(db_path: Path, seed: InsightSeed, *, owner_id: str) -> str:
    mid = f"m_insight_{uuid.uuid4().hex[:10]}"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
               confidence, is_shared, status, metadata_json, created_at, updated_at)
               VALUES(?, 'insight', ?, 0.7, ?, 0, 'active', ?,
               datetime('now'), datetime('now'))""",
            (mid, seed.summary, seed.confidence,
             json.dumps({
                 "source": "dream_cycle",
                 "source_memory_ids": seed.source_memory_ids,
             }, ensure_ascii=False)),
        )
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
            "VALUES(?, 'person', ?, NULL)", (mid, owner_id),
        )
        conn.commit()
    finally:
        conn.close()
    return mid


def run_dream_cycle(
    db_path: Path, *,
    min_cluster_size: int = 3, lookback_days: int = 30,
    archive_low_relevance: bool = True,
    relevance_threshold: float = 0.3,
) -> dict:
    """一次 dream cycle：压缩 + insight + learning。"""
    from we_together.services.forgetting_service import (
        archive_stale_memories, ForgetParams,
    )

    archived = {"archived_count": 0}
    if archive_low_relevance:
        try:
            archived = archive_stale_memories(
                db_path,
                ForgetParams(
                    max_relevance=relevance_threshold,
                    min_idle_days=max(7, lookback_days // 3),
                    dry_run=False,
                ),
            )
        except Exception as exc:
            archived = {"error": str(exc)}

    seeds = generate_insights(
        db_path, min_cluster_size=min_cluster_size, lookback_days=lookback_days,
    )

    # 把每个 insight 分配给第一个 owner（简化：同 cluster 内）
    created_insights: list[str] = []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        for seed in seeds:
            if not seed.source_memory_ids:
                continue
            row = conn.execute(
                "SELECT owner_id FROM memory_owners WHERE memory_id=? "
                "AND owner_type='person' LIMIT 1",
                (seed.source_memory_ids[0],),
            ).fetchone()
            if not row:
                continue
            owner_id = row["owner_id"]
            mid = persist_insight(db_path, seed, owner_id=owner_id)
            created_insights.append(mid)
    finally:
        conn.close()

    return {
        "archived": archived,
        "insight_seeds": len(seeds),
        "insights_created": created_insights,
    }
