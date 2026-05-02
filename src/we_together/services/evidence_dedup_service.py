"""Evidence hash 去重辅助：同一 evidence（基于内容 hash）二次导入时跳过。

SQLite 约束通过 raw_evidence.content_hash（migration 0001 原生有 metadata_json，我们
改走 evidence_hash 辅助表）。为了避免 schema 漂移，这里引入一个轻量辅助表
evidence_hash_registry（与现有 raw_evidence 并存），由 fusion_service 在落库前检查。

Phase 19 扩展：新增 pHash（感知哈希）用于图片去重，audio_fingerprint stub 用于音频。
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from we_together.db.connection import connect


def _ensure_hash_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS evidence_hash_registry (
            content_hash TEXT PRIMARY KEY,
            evidence_id TEXT NOT NULL,
            registered_at TEXT NOT NULL
        )"""
    )


def compute_evidence_hash(content: str, *, source_name: str = "") -> str:
    h = hashlib.sha256()
    h.update((source_name or "").encode("utf-8"))
    h.update(b"||")
    h.update(content.encode("utf-8"))
    return h.hexdigest()


def is_duplicate(db_path: Path, content_hash: str) -> bool:
    conn = connect(db_path)
    _ensure_hash_table(conn)
    row = conn.execute(
        "SELECT evidence_id FROM evidence_hash_registry WHERE content_hash = ?",
        (content_hash,),
    ).fetchone()
    conn.close()
    return row is not None


def register_evidence_hash(
    db_path: Path, content_hash: str, evidence_id: str, registered_at: str,
) -> None:
    conn = connect(db_path)
    _ensure_hash_table(conn)
    conn.execute(
        "INSERT OR IGNORE INTO evidence_hash_registry(content_hash, evidence_id, registered_at) "
        "VALUES(?, ?, ?)",
        (content_hash, evidence_id, registered_at),
    )
    conn.commit()
    conn.close()


# --- Phase 19 多模态 hash ---

def compute_image_phash(image_bytes: bytes) -> str:
    """极简 pHash：对 bytes 做 64 个等长 chunk 取 sum，
    用均值切分产生 64 位二进制串。不精确，但用于演示/去重足够。
    真实场景可替换为 imagehash 库。
    """
    if not image_bytes:
        return "0" * 64
    chunk_size = max(1, len(image_bytes) // 64)
    chunks = [image_bytes[i * chunk_size: (i + 1) * chunk_size]
              for i in range(64)]
    sums = [sum(c) for c in chunks]
    avg = sum(sums) / len(sums) if sums else 0
    return "".join("1" if s > avg else "0" for s in sums)


def phash_distance(a: str, b: str) -> int:
    if len(a) != len(b):
        return max(len(a), len(b))
    return sum(1 for x, y in zip(a, b) if x != y)


def is_duplicate_image(db_path: Path, image_hash: str,
                        *, threshold: int = 4) -> bool:
    conn = connect(db_path)
    _ensure_hash_table(conn)
    rows = conn.execute(
        "SELECT content_hash FROM evidence_hash_registry WHERE content_hash LIKE 'img:%'"
    ).fetchall()
    conn.close()
    for (h,) in rows:
        existing = h[4:]
        if phash_distance(existing, image_hash) <= threshold:
            return True
    return False


def compute_audio_fingerprint(audio_bytes: bytes, *, chunk_count: int = 32) -> str:
    if not audio_bytes:
        return "0" * chunk_count
    chunk_size = max(1, len(audio_bytes) // chunk_count)
    chunks = [audio_bytes[i * chunk_size: (i + 1) * chunk_size]
              for i in range(chunk_count)]
    sums = [sum(c) for c in chunks]
    avg = sum(sums) / len(sums) if sums else 0
    return "".join("1" if s > avg else "0" for s in sums)


def is_duplicate_audio(db_path: Path, fingerprint: str,
                         *, threshold: int = 2) -> bool:
    conn = connect(db_path)
    _ensure_hash_table(conn)
    rows = conn.execute(
        "SELECT content_hash FROM evidence_hash_registry WHERE content_hash LIKE 'aud:%'"
    ).fetchall()
    conn.close()
    for (h,) in rows:
        existing = h[4:]
        if phash_distance(existing, fingerprint) <= threshold:
            return True
    return False


def register_image_hash(db_path: Path, image_hash: str, evidence_id: str,
                         registered_at: str) -> None:
    register_evidence_hash(db_path, f"img:{image_hash}", evidence_id, registered_at)


def register_audio_hash(db_path: Path, fingerprint: str, evidence_id: str,
                         registered_at: str) -> None:
    register_evidence_hash(db_path, f"aud:{fingerprint}", evidence_id, registered_at)
