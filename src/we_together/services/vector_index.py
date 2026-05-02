"""Vector Index 抽象：支持 sqlite-vec / FAISS / 纯 Python fallback。

默认路径：纯 Python FlatIndex（线性扫全 BLOB），足够 1 万级；更大规模用:
  - sqlite-vec 扩展（延迟 import sqlite_vec）
  - FAISS（延迟 import faiss）

统一入口：
  idx = VectorIndex.build(db_path, target='memory', backend='auto')
  ids, scores = idx.query(query_vec, k=5)
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from we_together.db.connection import connect
from we_together.services.vector_similarity import (
    cosine_similarity,
    decode_vec,
    encode_vec,
    top_k,
)

TARGET_TABLES = {
    "memory": ("memory_embeddings", "memory_id"),
    "event": ("event_embeddings", "event_id"),
    "person": ("person_embeddings", "person_id"),
}

SUPPORTED_BACKENDS = {"auto", "flat_python", "sqlite_vec", "faiss"}


def _resolve_backend(backend: str) -> str:
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError(
            f"unknown backend: {backend}; supported: {sorted(SUPPORTED_BACKENDS)}"
        )
    if backend == "auto":
        return "flat_python"
    return backend


def _require_sqlite_vec():
    try:
        import sqlite_vec
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "sqlite_vec not installed: pip install sqlite-vec (v0.14 optional extra)"
        ) from exc
    return sqlite_vec


def _require_faiss():
    try:
        import faiss
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "faiss not installed: pip install faiss-cpu (v0.14 optional extra)"
        ) from exc
    return faiss


def _load_faiss_runtime():
    faiss = _require_faiss()
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "numpy not installed: pip install numpy faiss-cpu (faiss backend)"
        ) from exc
    return faiss, np


def _load_sqlite_vec_extension(conn: sqlite3.Connection) -> None:
    sqlite_vec = _require_sqlite_vec()
    try:
        conn.enable_load_extension(True)
    except Exception:
        pass

    if hasattr(sqlite_vec, "load"):
        sqlite_vec.load(conn)
    elif hasattr(sqlite_vec, "loadable_path"):
        conn.load_extension(sqlite_vec.loadable_path())
    else:  # pragma: no cover
        raise RuntimeError("sqlite_vec module missing load()/loadable_path()")

    try:
        conn.enable_load_extension(False)
    except Exception:
        pass


def _fetch_embedding_rows(
    db_path: Path,
    *,
    target: str,
    filter_person_ids: list[str] | None = None,
) -> list[tuple[str, bytes]]:
    table, id_col = TARGET_TABLES[target]
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if target == "memory" and filter_person_ids:
            placeholders = ",".join("?" for _ in filter_person_ids)
            rows = conn.execute(
                f"""SELECT DISTINCT e.{id_col} AS item_id, e.vec AS vec
                    FROM {table} e
                    JOIN memory_owners mo ON mo.memory_id = e.{id_col}
                    WHERE mo.owner_type = 'person' AND mo.owner_id IN ({placeholders})""",
                tuple(filter_person_ids),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {id_col} AS item_id, vec FROM {table}"
            ).fetchall()
    finally:
        conn.close()
    return [(r["item_id"], bytes(r["vec"])) for r in rows]


def _decode_items(rows: list[tuple[str, bytes]]) -> tuple[list[tuple[str, list[float]]], int]:
    items: list[tuple[str, list[float]]] = []
    dim = 0
    for item_id, blob in rows:
        vec = decode_vec(blob)
        if dim == 0:
            dim = len(vec)
        elif len(vec) != dim:
            raise ValueError(
                f"inconsistent vector dimensions: expected {dim}, got {len(vec)}"
            )
        items.append((item_id, vec))
    return items, dim


def _distance_to_similarity(distance: float) -> float:
    score = 1.0 - float(distance)
    return max(-1.0, min(1.0, score))


def _search_faiss_index(
    faiss_index: Any,
    id_map: list[str],
    query_vec: list[float],
    *,
    k: int,
) -> list[tuple[str, float]]:
    if not id_map or faiss_index is None or k <= 0:
        return []

    faiss, np = _load_faiss_runtime()
    query = np.asarray([list(query_vec)], dtype="float32")
    faiss.normalize_L2(query)
    limit = min(k, len(id_map))
    scores, indices = faiss_index.search(query, limit)
    score_row = scores[0] if len(scores) > 0 else []
    index_row = indices[0] if len(indices) > 0 else []

    out: list[tuple[str, float]] = []
    for item_index, score in zip(index_row, score_row, strict=False):
        item_index = int(item_index)
        if item_index < 0 or item_index >= len(id_map):
            continue
        out.append((id_map[item_index], float(score)))
    return out


def _build_faiss_index(
    rows: list[tuple[str, bytes]],
) -> tuple[Any | None, list[str], int]:
    items, dim = _decode_items(rows)
    if not items or dim == 0:
        return None, [], dim

    faiss, np = _load_faiss_runtime()
    matrix = np.asarray([vec for _, vec in items], dtype="float32")
    faiss.normalize_L2(matrix)
    index = faiss.IndexFlatIP(dim)
    index.add(matrix)
    return index, [item_id for item_id, _ in items], dim


def _query_sqlite_vec(
    db_path: Path,
    *,
    target: str,
    query_vec: list[float],
    k: int,
    filter_person_ids: list[str] | None = None,
) -> list[tuple[str, float]]:
    if k <= 0:
        return []

    table, id_col = TARGET_TABLES[target]
    query_blob = encode_vec(query_vec)
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _load_sqlite_vec_extension(conn)
        if target == "memory" and filter_person_ids:
            placeholders = ",".join("?" for _ in filter_person_ids)
            rows = conn.execute(
                f"""SELECT DISTINCT e.{id_col} AS item_id,
                           vec_distance_cosine(e.vec, ?) AS distance
                    FROM {table} e
                    JOIN memory_owners mo ON mo.memory_id = e.{id_col}
                    WHERE mo.owner_type = 'person' AND mo.owner_id IN ({placeholders})
                    ORDER BY distance ASC
                    LIMIT ?""",
                (query_blob, *filter_person_ids, k),
            ).fetchall()
        else:
            rows = conn.execute(
                f"""SELECT {id_col} AS item_id,
                           vec_distance_cosine(vec, ?) AS distance
                    FROM {table}
                    ORDER BY distance ASC
                    LIMIT ?""",
                (query_blob, k),
            ).fetchall()
    finally:
        conn.close()

    return [(r["item_id"], _distance_to_similarity(r["distance"])) for r in rows]


@dataclass
class VectorIndex:
    target: str
    backend: str
    items: list[tuple[str, list[float]]] | None = None
    db_path: Path | None = None
    faiss_index: Any | None = None
    id_map: list[str] | None = None
    dimension: int = 0
    size_hint: int = 0

    @classmethod
    def build(cls, db_path: Path, *, target: str, backend: str = "auto") -> VectorIndex:
        if target not in TARGET_TABLES:
            raise ValueError(f"unknown target: {target}")

        resolved = _resolve_backend(backend)
        rows = _fetch_embedding_rows(db_path, target=target)

        if resolved == "flat_python":
            items, dim = _decode_items(rows)
            return cls(
                target=target,
                backend="flat_python",
                items=items,
                dimension=dim,
                size_hint=len(items),
            )

        if resolved == "sqlite_vec":
            conn = connect(db_path)
            try:
                _load_sqlite_vec_extension(conn)
            finally:
                conn.close()
            return cls(
                target=target,
                backend="sqlite_vec",
                db_path=db_path,
                size_hint=len(rows),
            )

        if resolved == "faiss":
            index, id_map, dim = _build_faiss_index(rows)
            return cls(
                target=target,
                backend="faiss",
                db_path=db_path,
                faiss_index=index,
                id_map=id_map,
                dimension=dim,
                size_hint=len(id_map),
            )

        raise ValueError(f"unsupported backend: {resolved}")

    def query(self, query_vec: list[float], *, k: int = 5) -> list[tuple[str, float]]:
        if self.backend == "flat_python":
            return top_k(query_vec, self.items or [], k=k)
        if self.backend == "sqlite_vec":
            if self.db_path is None:
                return []
            return _query_sqlite_vec(
                self.db_path,
                target=self.target,
                query_vec=query_vec,
                k=k,
            )
        if self.backend == "faiss":
            return _search_faiss_index(
                self.faiss_index,
                self.id_map or [],
                query_vec,
                k=k,
            )
        return top_k(query_vec, self.items or [], k=k)

    def size(self) -> int:
        if self.backend == "flat_python":
            return len(self.items or [])
        if self.backend == "faiss":
            return len(self.id_map or [])
        return self.size_hint

    @classmethod
    def hierarchical_query(
        cls,
        db_path: Path,
        query_vec: list[float],
        *,
        target: str = "memory",
        filter_person_ids: list[str] | None = None,
        k: int = 5,
        backend: str = "auto",
    ) -> list[tuple[str, float]]:
        """先按 person 过滤候选 → 再 cosine 细排。"""
        resolved = _resolve_backend(backend)
        if target != "memory" or not filter_person_ids:
            return cls.build(db_path, target=target, backend=resolved).query(query_vec, k=k)

        if resolved == "sqlite_vec":
            return _query_sqlite_vec(
                db_path,
                target=target,
                query_vec=query_vec,
                filter_person_ids=filter_person_ids,
                k=k,
            )

        rows = _fetch_embedding_rows(
            db_path,
            target=target,
            filter_person_ids=filter_person_ids,
        )
        if resolved == "faiss":
            index, id_map, _ = _build_faiss_index(rows)
            return _search_faiss_index(index, id_map, query_vec, k=k)

        items, _ = _decode_items(rows)
        scored = [(item_id, cosine_similarity(query_vec, vec)) for item_id, vec in items]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]
