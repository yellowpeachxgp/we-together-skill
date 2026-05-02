"""Embedding backfill：给历史 memory/event/person 补算向量。

用法:
  we-together embed-backfill --root . --target memory --batch 50
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.db.connection import connect
from we_together.llm.providers.embedding import MockEmbeddingClient
from we_together.services.tenant_router import resolve_tenant_root
from we_together.services.vector_similarity import encode_vec


def _now() -> str:
    return datetime.now(UTC).isoformat()


TARGET_CONFIG = {
    "memory": {
        "table": "memory_embeddings",
        "source_table": "memories",
        "id_col": "memory_id",
        "text_col": "summary",
        "where": "status = 'active'",
    },
    "event": {
        "table": "event_embeddings",
        "source_table": "events",
        "id_col": "event_id",
        "text_col": "summary",
        "where": "summary IS NOT NULL AND summary != ''",
    },
    "person": {
        "table": "person_embeddings",
        "source_table": "persons",
        "id_col": "person_id",
        "text_col": "primary_name || ' ' || COALESCE(persona_summary, '')",
        "where": "status = 'active'",
    },
}


def backfill_embeddings(
    db_path: Path,
    *,
    target: str,
    embedding_client,
    batch: int = 50,
    limit: int | None = None,
) -> dict:
    cfg = TARGET_CONFIG.get(target)
    if not cfg:
        raise ValueError(f"unknown target: {target}")

    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    # 只处理未 embed 的
    query = (
        f"SELECT s.{cfg['id_col']} AS id, {cfg['text_col']} AS text "
        f"FROM {cfg['source_table']} s "
        f"LEFT JOIN {cfg['table']} e ON e.{cfg['id_col']} = s.{cfg['id_col']} "
        f"WHERE {cfg['where']} AND e.{cfg['id_col']} IS NULL"
    )
    if limit:
        query += f" LIMIT {int(limit)}"
    rows = conn.execute(query).fetchall()
    conn.close()

    if not rows:
        return {"target": target, "inserted": 0, "note": "nothing_to_backfill"}

    inserted = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        texts = [r["text"] or "" for r in chunk]
        vectors = embedding_client.embed(texts)
        conn = connect(db_path)
        now = _now()
        for row, vec in zip(chunk, vectors, strict=False):
            conn.execute(
                f"INSERT OR REPLACE INTO {cfg['table']}({cfg['id_col']}, "
                f"model_name, dim, vec, created_at) VALUES(?, ?, ?, ?, ?)",
                (row["id"], embedding_client.provider, embedding_client.dim,
                 encode_vec(vec), now),
            )
            inserted += 1
        conn.commit()
        conn.close()
    return {"target": target, "inserted": inserted,
             "model": embedding_client.provider, "dim": embedding_client.dim}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    ap.add_argument("--target", choices=list(TARGET_CONFIG), required=True)
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--provider", default="mock")
    args = ap.parse_args()

    tenant_root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    db = tenant_root / "db" / "main.sqlite3"
    if args.provider == "mock":
        client = MockEmbeddingClient()
    elif args.provider == "openai":
        from we_together.llm.providers.embedding import OpenAIEmbeddingClient
        client = OpenAIEmbeddingClient()
    elif args.provider == "sentence-transformers":
        from we_together.llm.providers.embedding import SentenceTransformersClient
        client = SentenceTransformersClient()
    else:
        print(f"unknown provider: {args.provider}", file=sys.stderr)
        return 2

    import json
    r = backfill_embeddings(db, target=args.target,
                             embedding_client=client,
                             batch=args.batch, limit=args.limit)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
