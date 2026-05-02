"""world_service（Phase 51 WM）：物 / 地点 / 项目 的 CRUD + 关联查询。

关联走 entity_links，不新建 join 表：
- person→owns→object: from_type='person' from_id=pid relation_type='owns' to_type='object' to_id=oid
- event→at→place: from_type='event' relation_type='at' to_type='place'
- project→involves→person: from_type='project' relation_type='involves' to_type='person'
- object→located_at→place: column location_place_id（直接外键更高效）

不变式 #26：所有世界对象必须有时间范围（effective_from / effective_until）。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# --- Objects ---

def register_object(
    db_path: Path, *,
    kind: str, name: str | None = None, description: str | None = None,
    owner_type: str | None = None, owner_id: str | None = None,
    location_place_id: str | None = None,
    effective_from: str | None = None,
    effective_until: str | None = None,
    metadata: dict | None = None,
) -> dict:
    oid = _new_id("obj")
    effective_from = effective_from or _now_iso()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO objects(object_id, kind, name, description, owner_type,
               owner_id, location_place_id, status, effective_from, effective_until,
               metadata_json, created_at, updated_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?,
               datetime('now'), datetime('now'))""",
            (oid, kind, name, description, owner_type, owner_id,
             location_place_id, effective_from, effective_until,
             json.dumps(metadata or {}, ensure_ascii=False)),
        )
        # 自动建 person→owns→object 关联
        if owner_type == "person" and owner_id:
            conn.execute(
                "INSERT INTO entity_links(from_type, from_id, relation_type, to_type, "
                "to_id, weight, metadata_json) VALUES('person', ?, 'owns', 'object', ?, "
                "1.0, '{}')", (owner_id, oid),
            )
        conn.commit()
    finally:
        conn.close()
    return {"object_id": oid, "kind": kind, "owner_id": owner_id}


def transfer_object(
    db_path: Path, *,
    object_id: str, new_owner_type: str, new_owner_id: str,
    event_id: str | None = None,
) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT owner_type, owner_id FROM objects WHERE object_id=?",
            (object_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"object not found: {object_id}")
        from_type, from_id = row["owner_type"], row["owner_id"]
        conn.execute(
            "UPDATE objects SET owner_type=?, owner_id=?, updated_at=datetime('now') "
            "WHERE object_id=?",
            (new_owner_type, new_owner_id, object_id),
        )
        conn.execute(
            """INSERT INTO object_ownership_history(object_id, from_owner_type,
               from_owner_id, to_owner_type, to_owner_id, event_id, recorded_at)
               VALUES(?, ?, ?, ?, ?, ?, datetime('now'))""",
            (object_id, from_type, from_id, new_owner_type, new_owner_id, event_id),
        )
        # 更新 entity_links
        if from_type == "person" and from_id:
            conn.execute(
                "DELETE FROM entity_links WHERE from_type='person' AND from_id=? "
                "AND relation_type='owns' AND to_type='object' AND to_id=?",
                (from_id, object_id),
            )
        if new_owner_type == "person":
            conn.execute(
                "INSERT INTO entity_links(from_type, from_id, relation_type, to_type, "
                "to_id, weight, metadata_json) VALUES('person', ?, 'owns', 'object', ?, "
                "1.0, '{}')",
                (new_owner_id, object_id),
            )
        conn.commit()
    finally:
        conn.close()
    return {
        "object_id": object_id,
        "from": {"type": from_type, "id": from_id},
        "to": {"type": new_owner_type, "id": new_owner_id},
    }


def list_objects_by_owner(
    db_path: Path, owner_type: str, owner_id: str, *, limit: int = 50,
) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT object_id, kind, name, description, status, effective_from,
               effective_until FROM objects
               WHERE owner_type=? AND owner_id=? AND status='active'
               ORDER BY created_at DESC LIMIT ?""",
            (owner_type, owner_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Places ---

def register_place(
    db_path: Path, *,
    name: str, scope: str | None = None, description: str | None = None,
    parent_place_id: str | None = None,
    effective_from: str | None = None,
    effective_until: str | None = None,
    metadata: dict | None = None,
) -> dict:
    pid = _new_id("place")
    effective_from = effective_from or _now_iso()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO places(place_id, name, description, scope, parent_place_id,
               visibility, status, effective_from, effective_until, metadata_json,
               created_at, updated_at)
               VALUES(?, ?, ?, ?, ?, 'shared', 'active', ?, ?, ?,
               datetime('now'), datetime('now'))""",
            (pid, name, description, scope, parent_place_id,
             effective_from, effective_until,
             json.dumps(metadata or {}, ensure_ascii=False)),
        )
        conn.commit()
    finally:
        conn.close()
    return {"place_id": pid, "name": name}


def get_place_lineage(db_path: Path, place_id: str) -> list[dict]:
    """返回从根祖先到 place_id 的父链。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        visited: set[str] = set()
        chain: list[dict] = []
        current = place_id
        while current and current not in visited:
            visited.add(current)
            row = conn.execute(
                "SELECT place_id, name, parent_place_id FROM places WHERE place_id=?",
                (current,),
            ).fetchone()
            if not row:
                break
            chain.append({"place_id": row["place_id"], "name": row["name"]})
            current = row["parent_place_id"]
        return list(reversed(chain))
    finally:
        conn.close()


def link_event_to_place(db_path: Path, event_id: str, place_id: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO entity_links(from_type, from_id, relation_type, to_type, to_id, "
            "weight, metadata_json) VALUES('event', ?, 'at', 'place', ?, 1.0, '{}')",
            (event_id, place_id),
        )
        conn.commit()
    finally:
        conn.close()


# --- Projects ---

def register_project(
    db_path: Path, *,
    name: str, goal: str | None = None, description: str | None = None,
    priority: str | None = None,
    started_at: str | None = None, due_at: str | None = None,
    participants: list[str] | None = None,
    metadata: dict | None = None,
) -> dict:
    pid = _new_id("proj")
    started_at = started_at or _now_iso()
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO projects(project_id, name, goal, description, status,
               priority, started_at, due_at, metadata_json, created_at, updated_at)
               VALUES(?, ?, ?, ?, 'active', ?, ?, ?, ?,
               datetime('now'), datetime('now'))""",
            (pid, name, goal, description, priority, started_at, due_at,
             json.dumps(metadata or {}, ensure_ascii=False)),
        )
        for person_id in (participants or []):
            conn.execute(
                "INSERT INTO entity_links(from_type, from_id, relation_type, to_type, "
                "to_id, weight, metadata_json) VALUES('project', ?, 'involves', 'person', "
                "?, 1.0, '{}')",
                (pid, person_id),
            )
        conn.commit()
    finally:
        conn.close()
    return {"project_id": pid, "name": name, "participants": list(participants or [])}


def set_project_status(db_path: Path, project_id: str, status: str) -> dict:
    valid = {"active", "completed", "abandoned", "archived"}
    if status not in valid:
        raise ValueError(f"invalid status: {status}; must be in {sorted(valid)}")
    conn = sqlite3.connect(db_path)
    try:
        ended = "datetime('now')" if status in {"completed", "abandoned", "archived"} else "NULL"
        conn.execute(
            f"UPDATE projects SET status=?, ended_at={ended}, "
            "updated_at=datetime('now') WHERE project_id=?",
            (status, project_id),
        )
        conn.commit()
    finally:
        conn.close()
    return {"project_id": project_id, "status": status}


def list_projects_for_person(db_path: Path, person_id: str) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT p.project_id, p.name, p.goal, p.status, p.priority, p.due_at
               FROM projects p
               JOIN entity_links e ON e.from_type='project' AND e.from_id=p.project_id
                 AND e.relation_type='involves' AND e.to_type='person'
               WHERE e.to_id=? AND p.status='active'
               ORDER BY p.created_at DESC""",
            (person_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# --- Retrieval 辅助 ---

def active_world_for_scene(db_path: Path, scene_id: str) -> dict:
    """返回 scene 当前"活跃世界"：参与者 / 相关 objects / 相关 places / active projects。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # 场景参与者
        participants = [r[0] for r in conn.execute(
            "SELECT person_id FROM scene_participants WHERE scene_id=?",
            (scene_id,),
        ).fetchall()]
        if not participants:
            return {"participants": [], "objects": [], "places": [], "projects": []}
        placeholders = ",".join("?" * len(participants))
        # 参与者拥有的 objects
        objects = [dict(r) for r in conn.execute(
            f"""SELECT object_id, kind, name, owner_id FROM objects
                WHERE owner_type='person' AND owner_id IN ({placeholders})
                AND status='active' LIMIT 30""",
            participants,
        ).fetchall()]
        # 参与者涉及的 projects
        projects = [dict(r) for r in conn.execute(
            f"""SELECT DISTINCT p.project_id, p.name, p.goal, p.status
                FROM projects p
                JOIN entity_links e ON e.from_type='project' AND e.from_id=p.project_id
                  AND e.relation_type='involves' AND e.to_type='person'
                WHERE e.to_id IN ({placeholders}) AND p.status='active'
                LIMIT 10""",
            participants,
        ).fetchall()]
        # 通过 event→at→place 反查 scene 相关 place
        places = [dict(r) for r in conn.execute(
            """SELECT DISTINCT p.place_id, p.name, p.scope FROM places p
               JOIN entity_links e ON e.from_type='event' AND e.relation_type='at'
                 AND e.to_type='place' AND e.to_id=p.place_id
               JOIN events ev ON ev.event_id=e.from_id
               WHERE ev.scene_id=? AND p.status='active' LIMIT 10""",
            (scene_id,),
        ).fetchall()]
    finally:
        conn.close()
    return {
        "participants": participants,
        "objects": objects,
        "places": places,
        "projects": projects,
    }
