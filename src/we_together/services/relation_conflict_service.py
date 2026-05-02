"""关系冲突检测：对窗口期内 relation 相关 events 做 sentiment 分析，
识别"正/负情绪反复震荡"的关系作为冲突候选。

检测信号：
  - 时间升序扫事件 sentiment（+1/-1/0），统计符号切换次数 (reversals)
  - reversals >= min_reversals 视为冲突候选
  - 同时上报 positive_count / negative_count / 样本摘要

输出：
  - 不修改主图；返回 details 供上层决策
  - emit_memory=True 时，为每个冲突写一条 conflict_signal memory patch（低置信），
    owner 为该 relation 关联事件的 participants 并集
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.relation_drift_service import _score_event_sentiment


def _fetch_relation_event_rows(
    conn: sqlite3.Connection,
    relation_id: str,
    window_start: datetime,
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT e.event_id, e.timestamp, e.summary
        FROM events e
        JOIN event_targets et ON et.event_id = e.event_id
        WHERE et.target_type = 'relation' AND et.target_id = ?
          AND (e.timestamp IS NULL OR e.timestamp >= ?)
        ORDER BY e.timestamp ASC
        """,
        (relation_id, window_start.isoformat()),
    ).fetchall()


def _analyze_reversals(rows: list[sqlite3.Row]) -> dict:
    sentiments: list[int] = []
    positive = 0
    negative = 0
    samples: list[str] = []
    for row in rows:
        s = _score_event_sentiment(row["summary"])
        if s == 0:
            continue
        sentiments.append(s)
        if s > 0:
            positive += 1
        else:
            negative += 1
        if len(samples) < 5:
            samples.append(row["summary"] or "")

    reversals = 0
    for i in range(1, len(sentiments)):
        if sentiments[i] != sentiments[i - 1]:
            reversals += 1

    return {
        "reversals": reversals,
        "positive_count": positive,
        "negative_count": negative,
        "sample_summaries": samples,
    }


def detect_relation_conflicts(
    db_path: Path,
    *,
    window_days: int = 30,
    min_reversals: int = 2,
    limit: int = 200,
    emit_memory: bool = False,
    source_event_id: str | None = None,
) -> dict:
    window_start = datetime.now(UTC) - timedelta(days=window_days)

    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    relations = conn.execute(
        """
        SELECT relation_id FROM relations
        WHERE status = 'active'
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    details: list[dict] = []
    memory_patches: list[tuple[str, list[str], dict]] = []
    for rel in relations:
        rid = rel["relation_id"]
        rows = _fetch_relation_event_rows(conn, rid, window_start)
        analysis = _analyze_reversals(rows)
        if analysis["reversals"] < min_reversals:
            continue
        # 收集 participants 以便 memory owner
        participants = [
            r["person_id"]
            for r in conn.execute(
                """
                SELECT DISTINCT ep.person_id
                FROM event_participants ep
                JOIN event_targets et ON et.event_id = ep.event_id
                WHERE et.target_type = 'relation' AND et.target_id = ?
                """,
                (rid,),
            ).fetchall()
        ]
        detail = {"relation_id": rid, **analysis, "participants": participants}
        details.append(detail)
        if emit_memory and participants:
            memory_patches.append((rid, participants, analysis))
    conn.close()

    for rid, participants, analysis in memory_patches:
        memory_id = f"mem_conflict_{uuid.uuid4().hex[:10]}"
        summary = (
            f"关系 {rid} 近期出现 {analysis['reversals']} 次情绪反转"
            f"（正 {analysis['positive_count']} / 负 {analysis['negative_count']}）"
        )
        patch = build_patch(
            source_event_id=source_event_id or f"conflict_{rid}",
            target_type="memory",
            target_id=memory_id,
            operation="create_memory",
            payload={
                "memory_id": memory_id,
                "memory_type": "conflict_signal",
                "summary": summary,
                "relevance_score": 0.55,
                "confidence": 0.4,
                "is_shared": 1,
                "status": "active",
                "metadata_json": {
                    "relation_id": rid,
                    "reversals": analysis["reversals"],
                    "positive_count": analysis["positive_count"],
                    "negative_count": analysis["negative_count"],
                },
            },
            confidence=0.4,
            reason=f"conflict detector: {analysis['reversals']} reversals",
        )
        apply_patch_record(db_path=db_path, patch=patch)
        # owners 独立写入（patch_applier 的 create_memory 不处理 owners）
        owner_conn = connect(db_path)
        for pid in participants:
            owner_conn.execute(
                "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
                "VALUES(?, 'person', ?, 'conflict_party')",
                (memory_id, pid),
            )
        owner_conn.commit()
        owner_conn.close()

    return {
        "conflict_count": len(details),
        "window_days": window_days,
        "min_reversals": min_reversals,
        "details": details,
    }
