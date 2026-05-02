"""Associative memory recall (ND-3 stub)：基于主题的联想式记忆触发。

给定 seed memory / 主题词，LLM 找出相关 memory 列表。不改图谱，只返回候选列表。
完整实现需要配合 persona / narrative arc，留 Phase 24 后续扩展。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm import LLMMessage, get_llm_client


def associate_memories(
    db_path: Path, *, seed_text: str, limit: int = 50, top_k: int = 5,
    llm_client=None,
) -> dict:
    client = llm_client or get_llm_client()
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT memory_id, summary FROM memories WHERE status = 'active' "
        "ORDER BY relevance_score DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    if not rows:
        return {"associated": [], "seed": seed_text}

    bullets = "\n".join(f"- [{r['memory_id']}] {r['summary']}" for r in rows)
    try:
        payload = client.chat_json(
            [
                LLMMessage(role="system",
                            content="你是联想式记忆触发器，从候选池里挑出与主题最相关的记忆。"),
                LLMMessage(role="user",
                            content=(
                                f"主题：{seed_text}\n\n候选池:\n{bullets}\n\n"
                                f"请输出 JSON: {{\"associated\": [memory_id, ...]}}（最多 {top_k} 条）"
                            )),
            ],
            schema_hint={"associated": "list"},
        )
    except Exception as exc:
        return {"associated": [], "seed": seed_text, "error": str(exc)}

    associated = [m for m in (payload.get("associated") or [])
                   if any(r["memory_id"] == m for r in rows)][:top_k]
    return {"associated": associated, "seed": seed_text,
             "candidate_count": len(rows)}
