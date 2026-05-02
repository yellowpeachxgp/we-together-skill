"""Embedding-based associative recall (VE-4)。

替代 Phase 24 的 LLM 联想 stub。给定 seed_text:
  1. 如 embedding_client 可用 → embed(seed) + top_k over memory_embeddings
  2. 否则 → fallback 到 services/associative_recall.associate_memories（LLM）
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.vector_similarity import cosine_similarity, decode_vec


def associate_by_embedding(
    db_path: Path,
    *,
    seed_text: str,
    embedding_client,
    top_k: int = 5,
    model_filter: str | None = None,
    filter_person_ids: list[str] | None = None,
    index_backend: str = "auto",
) -> dict:
    if embedding_client is None:
        return {"associated": [], "seed": seed_text,
                 "reason": "no_embedding_client"}

    query_vec = embedding_client.embed([seed_text])[0]

    from we_together.services.vector_index import VectorIndex

    # 层级检索：过滤 person_ids 时走 hierarchical_query
    if filter_person_ids:
        top = VectorIndex.hierarchical_query(
            db_path, query_vec, target="memory",
            filter_person_ids=filter_person_ids, k=top_k,
            backend=index_backend,
        )
        return {
            "associated": [mid for mid, _ in top],
            "scores": [round(s, 4) for _, s in top],
            "seed": seed_text,
            "mode": "hierarchical",
        }

    if model_filter is None:
        idx = VectorIndex.build(db_path, target="memory", backend=index_backend)
        top = idx.query(query_vec, k=top_k)
        if not top:
            return {
                "associated": [],
                "seed": seed_text,
                "reason": "no_embeddings_indexed",
                "candidate_count": idx.size(),
                "backend": idx.backend,
            }
        return {
            "associated": [mid for mid, _ in top],
            "scores": [round(s, 4) for _, s in top],
            "seed": seed_text,
            "candidate_count": idx.size(),
            "backend": idx.backend,
        }

    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    if model_filter:
        rows = conn.execute(
            "SELECT memory_id, vec FROM memory_embeddings WHERE model_name = ?",
            (model_filter,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT memory_id, vec FROM memory_embeddings"
        ).fetchall()
    conn.close()

    if not rows:
        return {"associated": [], "seed": seed_text,
                 "reason": "no_embeddings_indexed",
                 "candidate_count": 0}

    scored: list[tuple[str, float]] = []
    for r in rows:
        sim = cosine_similarity(query_vec, decode_vec(r["vec"]))
        scored.append((r["memory_id"], sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:top_k]
    return {
        "associated": [mid for mid, _ in top],
        "scores": [round(s, 4) for _, s in top],
        "seed": seed_text,
        "candidate_count": len(rows),
    }
