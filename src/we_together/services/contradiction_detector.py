"""Contradiction detector（Phase 31 MC-1）。

扫 memories，用 embedding 相似度过滤可能冲突的对，再用 LLM 判定。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm import LLMMessage
from we_together.services.vector_similarity import cosine_similarity, decode_vec


def _fetch_memory_embeddings(conn: sqlite3.Connection) -> list[tuple[str, str, list[float]]]:
    rows = conn.execute(
        """SELECT m.memory_id, m.summary, e.vec
           FROM memories m
           JOIN memory_embeddings e ON e.memory_id=m.memory_id
           WHERE m.status='active'""",
    ).fetchall()
    return [(r["memory_id"], r["summary"], decode_vec(r["vec"])) for r in rows]


def find_candidate_pairs(
    db_path: Path, *, similarity_min: float = 0.7,
) -> list[tuple[str, str, float]]:
    """embedding 相似度 >= 阈值的候选对（可能同一主题，需 LLM 判定是否冲突）。"""
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    items = _fetch_memory_embeddings(conn)
    conn.close()
    pairs: list[tuple[str, str, float]] = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            sim = cosine_similarity(items[i][2], items[j][2])
            if sim >= similarity_min:
                pairs.append((items[i][0], items[j][0], sim))
    return pairs


def judge_contradiction(
    summary_a: str, summary_b: str, *, llm_client,
) -> dict:
    try:
        payload = llm_client.chat_json(
            [
                LLMMessage(role="system",
                            content="你判断两条记忆是否直接矛盾。只输出 JSON。"),
                LLMMessage(role="user",
                            content=(
                                f"A: {summary_a}\nB: {summary_b}\n\n"
                                "请输出 JSON: {\"is_contradiction\": bool, "
                                "\"confidence\": 0..1, \"reason\": str}"
                            )),
            ],
            schema_hint={"is_contradiction": "bool", "confidence": "float",
                          "reason": "str"},
        )
    except Exception as exc:
        return {"is_contradiction": False, "confidence": 0.0,
                 "reason": f"error: {exc}"}
    return {
        "is_contradiction": bool(payload.get("is_contradiction")),
        "confidence": float(payload.get("confidence") or 0.0),
        "reason": str(payload.get("reason", "")),
    }


def detect_contradictions(
    db_path: Path, *, similarity_min: float = 0.7, llm_client,
) -> dict:
    candidates = find_candidate_pairs(db_path, similarity_min=similarity_min)
    if not candidates:
        return {"candidate_count": 0, "contradiction_count": 0, "contradictions": []}

    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    contradictions: list[dict] = []
    for a_id, b_id, sim in candidates:
        row_a = conn.execute(
            "SELECT summary FROM memories WHERE memory_id = ?", (a_id,),
        ).fetchone()
        row_b = conn.execute(
            "SELECT summary FROM memories WHERE memory_id = ?", (b_id,),
        ).fetchone()
        if not (row_a and row_b):
            continue
        judged = judge_contradiction(row_a["summary"], row_b["summary"],
                                      llm_client=llm_client)
        if judged["is_contradiction"]:
            contradictions.append({
                "memory_a": a_id, "memory_b": b_id, "similarity": round(sim, 3),
                **judged,
            })
    conn.close()
    return {
        "candidate_count": len(candidates),
        "contradiction_count": len(contradictions),
        "contradictions": contradictions,
    }
