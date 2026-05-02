"""Embedding retrieval eval。"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.embedding_recall import associate_by_embedding
from we_together.services.vector_similarity import encode_vec


def run_embedding_retrieval_eval(
    db_path: Path, benchmark_path: Path, *, embedding_client,
) -> dict:
    data = json.loads(benchmark_path.read_text(encoding="utf-8"))

    # 先 backfill seed memories
    conn = connect(db_path)
    now = datetime.now(UTC).isoformat()
    for mem in data.get("seed_memories", []):
        try:
            conn.execute(
                """INSERT OR IGNORE INTO memories(memory_id, memory_type, summary,
                   relevance_score, confidence, is_shared, status, metadata_json,
                   created_at, updated_at) VALUES(?, 'shared_memory', ?, 0.7, 0.7, 1,
                   'active', '{}', ?, ?)""",
                (mem["memory_id"], mem["summary"], now, now),
            )
        except sqlite3.IntegrityError:
            pass
        vec = embedding_client.embed([mem["summary"]])[0]
        conn.execute(
            """INSERT OR REPLACE INTO memory_embeddings(memory_id, model_name, dim,
               vec, created_at) VALUES(?, ?, ?, ?, ?)""",
            (mem["memory_id"], embedding_client.provider,
             embedding_client.dim, encode_vec(vec), now),
        )
    conn.commit()
    conn.close()

    results: list[dict] = []
    passed = 0
    for q in data.get("queries", []):
        recall = associate_by_embedding(
            db_path, seed_text=q["seed_text"],
            embedding_client=embedding_client, top_k=5,
        )
        top = set(recall.get("associated", []))
        expected = set(q.get("expected_top_ids", []))
        hits = len(top & expected)
        min_hits = q.get("min_hits_in_top_k", 1)
        ok = hits >= min_hits
        if ok:
            passed += 1
        results.append({
            "seed": q["seed_text"],
            "expected": list(expected),
            "top": list(top),
            "hits": hits,
            "passed": ok,
        })

    total = len(results)
    return {
        "benchmark": data.get("benchmark_name"),
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "queries": results,
    }
