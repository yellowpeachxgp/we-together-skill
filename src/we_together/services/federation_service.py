"""联邦引用服务：把远端 skill 的 person 注册为本地 ref，retrieval 按 policy 加载。

最小能力：
  - register_external_person(...)：写一行 external_person_refs
  - list_external_refs(policy=None)：按 policy 过滤
  - 不做真实网络调用；上层决定何时去加载远端数据
"""
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect


def _now() -> str:
    return datetime.now(UTC).isoformat()


def register_external_person(
    db_path: Path,
    *,
    external_skill_name: str,
    external_person_id: str,
    display_name: str | None = None,
    local_alias: str | None = None,
    trust_level: float = 0.5,
    policy: str = "lazy",
    metadata: dict | None = None,
) -> str:
    ref_id = f"extref_{uuid.uuid4().hex[:12]}"
    now = _now()
    conn = connect(db_path)
    conn.execute(
        """INSERT OR REPLACE INTO external_person_refs(
            ref_id, external_skill_name, external_person_id, local_alias,
            display_name, trust_level, policy, metadata_json, created_at, updated_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (ref_id, external_skill_name, external_person_id, local_alias,
         display_name, trust_level, policy,
         json.dumps(metadata or {}, ensure_ascii=False), now, now),
    )
    conn.commit()
    conn.close()
    return ref_id


def list_external_refs(db_path: Path, *, policy: str | None = None) -> list[dict]:
    conn = connect(db_path)
    if policy:
        rows = conn.execute(
            "SELECT ref_id, external_skill_name, external_person_id, local_alias, "
            "display_name, trust_level, policy, metadata_json FROM external_person_refs "
            "WHERE policy = ?",
            (policy,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT ref_id, external_skill_name, external_person_id, local_alias, "
            "display_name, trust_level, policy, metadata_json FROM external_person_refs"
        ).fetchall()
    conn.close()
    return [
        {
            "ref_id": r[0],
            "external_skill_name": r[1],
            "external_person_id": r[2],
            "local_alias": r[3],
            "display_name": r[4],
            "trust_level": r[5],
            "policy": r[6],
            "metadata": json.loads(r[7] or "{}"),
        }
        for r in rows
    ]


def get_eager_refs(db_path: Path) -> list[dict]:
    """retrieval 层可直接加载的 eager 引用。"""
    return list_external_refs(db_path, policy="eager")
