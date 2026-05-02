"""Retrieval cache 预热：遍历 active scenes 预先调 build 产生缓存。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.runtime.sqlite_retrieval import build_runtime_retrieval_package_from_db


def warm_retrieval_cache(
    db_path: Path, *, limit: int | None = 50, input_hash: str = "warmup",
) -> dict:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT scene_id FROM scenes WHERE status = 'active' ORDER BY updated_at DESC LIMIT ?",
        (limit or 50,),
    ).fetchall()
    conn.close()
    warmed: list[str] = []
    errors: list[dict] = []
    for (scene_id,) in rows:
        try:
            build_runtime_retrieval_package_from_db(
                db_path=db_path, scene_id=scene_id, input_hash=input_hash,
            )
            warmed.append(scene_id)
        except Exception as exc:
            errors.append({"scene_id": scene_id, "error": str(exc)})
    return {"warmed_count": len(warmed), "errors": errors}
