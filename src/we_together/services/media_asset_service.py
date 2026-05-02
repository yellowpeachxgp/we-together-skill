"""media_asset_service（Phase 35 MM-2/3/14/15）：媒体资产的登记 / 查询 / 去重 / 可见性。

职责：
- register(kind, path, owner_id, ...) → media_id；hash 命中则返回旧 media_id（去重）
- list_by_owner / list_by_scene
- link_to_memory(media_id, memory_id) 等

设计：
- hash 用 sha256(content) 去重
- visibility ∈ {private, shared, group}；retrieval_package 据此过滤
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from pathlib import Path


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _new_media_id() -> str:
    return f"media_{uuid.uuid4().hex[:12]}"


def register(
    db_path: Path, *,
    kind: str,
    content: bytes | None = None,
    path: str | None = None,
    owner_id: str | None = None,
    owner_type: str = "person",
    visibility: str = "private",
    scene_id: str | None = None,
    summary: str | None = None,
    mime_type: str | None = None,
    metadata: dict | None = None,
) -> dict:
    """登记媒体资产。若 content_hash 已存在则返回旧记录。"""
    if content is None and path is None:
        raise ValueError("content or path required")

    if content is None:
        p = Path(path)
        content = p.read_bytes() if p.exists() else path.encode("utf-8")

    h = _sha256(content)
    size = len(content)

    conn = sqlite3.connect(db_path)
    try:
        # hash-dedup：同 owner 下同 hash 视为同一资源
        row = conn.execute(
            "SELECT media_id FROM media_assets WHERE content_hash=? "
            "AND COALESCE(owner_id,'')=COALESCE(?, '')",
            (h, owner_id),
        ).fetchone()
        if row:
            return {"media_id": row[0], "dedup": True}

        media_id = _new_media_id()
        conn.execute(
            """INSERT INTO media_assets(media_id, kind, path, content_hash, mime_type,
               size_bytes, owner_type, owner_id, visibility, scene_id, summary,
               metadata_json, created_at, updated_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
               datetime('now'), datetime('now'))""",
            (media_id, kind, path, h, mime_type, size, owner_type, owner_id,
             visibility, scene_id, summary,
             json.dumps(metadata or {}, ensure_ascii=False)),
        )
        conn.commit()
        return {"media_id": media_id, "dedup": False, "content_hash": h}
    finally:
        conn.close()


def list_by_owner(db_path: Path, owner_id: str, *, limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT media_id, kind, summary, visibility, created_at "
            "FROM media_assets WHERE owner_id=? ORDER BY created_at DESC LIMIT ?",
            (owner_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_by_scene(db_path: Path, scene_id: str, *, limit: int = 50) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT media_id, kind, summary, visibility, owner_id, created_at "
            "FROM media_assets WHERE scene_id=? ORDER BY created_at DESC LIMIT ?",
            (scene_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def link_to_memory(db_path: Path, media_id: str, memory_id: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO media_refs(media_id, target_type, target_id) "
            "VALUES(?, 'memory', ?)",
            (media_id, memory_id),
        )
        conn.commit()
    finally:
        conn.close()


def link_to_event(db_path: Path, media_id: str, event_id: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO media_refs(media_id, target_type, target_id) "
            "VALUES(?, 'event', ?)",
            (media_id, event_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_media_for_memory(db_path: Path, memory_id: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT a.media_id, a.kind, a.summary, a.visibility "
            "FROM media_assets a JOIN media_refs r ON r.media_id=a.media_id "
            "WHERE r.target_type='memory' AND r.target_id=?",
            (memory_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def filter_by_visibility(items: list[dict], viewer_id: str | None = None) -> list[dict]:
    """retrieval 层过滤：private 只返回 owner；shared/group 全返。"""
    out: list[dict] = []
    for it in items:
        vis = it.get("visibility", "private")
        if vis == "private":
            if viewer_id is None or it.get("owner_id") == viewer_id:
                out.append(it)
        else:
            out.append(it)
    return out
