"""Local HTTP bridge between the WebUI and the we-together skill runtime.

The browser talks to this process on 127.0.0.1 and does not own provider API
tokens. Provider selection and keys stay in the current CLI environment.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.seed_demo import seed_society_c
from we_together.db.bootstrap import bootstrap_project
from we_together.llm import get_llm_client
from we_together.services.chat_service import run_turn
from we_together.services.ingestion_service import ingest_narration
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch
from we_together.services.tenant_router import infer_tenant_id_from_root, resolve_tenant_root
from we_together.services.world_service import active_world_for_scene


class BridgeConfig:
    def __init__(
        self,
        *,
        root: Path,
        tenant_id: str | None = None,
        provider: str | None = None,
        adapter: str = "claude",
    ) -> None:
        self.root = root
        self.tenant_id = tenant_id
        self.provider = provider
        self.adapter = adapter


def _resolved_provider_name(provider: str | None) -> str:
    return (provider or os.environ.get("WE_TOGETHER_LLM_PROVIDER") or "mock").lower().strip()


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _response_text(response: dict) -> str:
    response_payload = response.get("response") or {}
    return str(response_payload.get("text") or "")


def _tenant_root(root: Path, tenant_id: str | None) -> Path:
    return resolve_tenant_root(Path(root).resolve(), tenant_id)


def _tenant_db_path(root: Path, tenant_id: str | None) -> Path:
    return _tenant_root(root, tenant_id) / "db" / "main.sqlite3"


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row is not None


def _row_dict(row: sqlite3.Row | None) -> dict:
    return dict(row) if row is not None else {}


def _json_loads(value, fallback=None):
    if fallback is None:
        fallback = {}
    if value in (None, ""):
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _select_rows(
    conn: sqlite3.Connection,
    query: str,
    params: tuple = (),
    *,
    table: str,
) -> list[dict]:
    if not _table_exists(conn, table):
        return []
    try:
        return [dict(row) for row in conn.execute(query, params).fetchall()]
    except sqlite3.Error:
        return []


def _count_table(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    suffix = f" WHERE {where}" if where else ""
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}{suffix}").fetchone()
    except sqlite3.Error:
        return 0
    return int(row[0] if row else 0)


def _node(node_id: str, label: str, node_type: str, *, scene_id: str | None = None, active: bool = False, data: dict | None = None) -> dict:
    return {
        "id": node_id,
        "label": label or node_id,
        "type": node_type,
        "scene_id": scene_id,
        "active_in_scene": active,
        "data": data or {},
    }


def _edge(edge_id: str, source: str, target: str, label: str, edge_type: str) -> dict:
    return {
        "id": edge_id,
        "source": source,
        "target": target,
        "label": label,
        "type": edge_type,
    }


def build_local_summary(*, root: Path, tenant_id: str | None) -> dict:
    tenant_root = _tenant_root(root, tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    if not db_path.exists():
        return {
            "source": "local_skill",
            "db_exists": False,
            "tenant_id": infer_tenant_id_from_root(tenant_root),
            "person_count": 0,
            "relation_count": 0,
            "memory_count": 0,
            "event_count": 0,
            "patch_count": 0,
            "snapshot_count": 0,
            "open_local_branch_count": 0,
        }
    conn = sqlite3.connect(db_path)
    try:
        return {
            "source": "local_skill",
            "db_exists": True,
            "tenant_id": infer_tenant_id_from_root(tenant_root),
            "person_count": _count_table(conn, "persons", "status='active'"),
            "relation_count": _count_table(conn, "relations", "status='active'"),
            "memory_count": _count_table(conn, "memories", "status='active'"),
            "event_count": _count_table(conn, "events"),
            "patch_count": _count_table(conn, "patches"),
            "snapshot_count": _count_table(conn, "snapshots"),
            "open_local_branch_count": _count_table(conn, "local_branches", "status='open'"),
        }
    finally:
        conn.close()


def list_local_scenes(*, root: Path, tenant_id: str | None) -> dict:
    db_path = _tenant_db_path(root, tenant_id)
    if not db_path.exists():
        return {"source": "local_skill", "scenes": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT scene_id, scene_type, scene_summary, status "
            "FROM scenes WHERE status='active' ORDER BY updated_at DESC, created_at DESC, scene_id"
        ).fetchall()
        scenes = []
        for row in rows:
            participant_count = 0
            try:
                participant_count = int(
                    conn.execute(
                        "SELECT COUNT(*) FROM scene_participants WHERE scene_id = ?",
                        (row["scene_id"],),
                    ).fetchone()[0]
                )
            except sqlite3.Error:
                participant_count = 0
            scenes.append(
                {
                    "scene_id": row["scene_id"],
                    "scene_type": row["scene_type"],
                    "scene_summary": row["scene_summary"],
                    "status": row["status"],
                    "participant_count": participant_count,
                }
            )
        return {"source": "local_skill", "scenes": scenes}
    finally:
        conn.close()


def build_local_graph(*, root: Path, tenant_id: str | None, scene_id: str | None = None) -> dict:
    db_path = _tenant_db_path(root, tenant_id)
    if not db_path.exists():
        return {"source": "local_skill", "nodes": [], "edges": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}
    try:
        active_scene_people = set()
        active_scene_groups = set()
        if scene_id and _table_exists(conn, "scene_participants"):
            active_scene_people = {
                row["person_id"]
                for row in conn.execute("SELECT person_id FROM scene_participants WHERE scene_id = ?", (scene_id,))
            }
        if scene_id and _table_exists(conn, "scenes"):
            row = conn.execute("SELECT group_id FROM scenes WHERE scene_id = ?", (scene_id,)).fetchone()
            if row and row["group_id"]:
                active_scene_groups.add(row["group_id"])

        for row in _select_rows(
            conn,
            "SELECT * FROM persons WHERE status='active' ORDER BY person_id LIMIT 80",
            table="persons",
        ):
            node_id = row["person_id"]
            nodes[node_id] = _node(
                node_id,
                row.get("primary_name") or node_id,
                "person",
                scene_id=scene_id if node_id in active_scene_people else None,
                active=node_id in active_scene_people,
                data=row,
            )

        for row in _select_rows(
            conn,
            "SELECT * FROM memories WHERE status='active' ORDER BY memory_id LIMIT 80",
            table="memories",
        ):
            node_id = row["memory_id"]
            nodes[node_id] = _node(
                node_id,
                row.get("summary") or node_id,
                "memory",
                active=False,
                data={**row, "metadata_json": _json_loads(row.get("metadata_json"))},
            )

        for row in _select_rows(
            conn,
            "SELECT * FROM relations WHERE status='active' ORDER BY relation_id LIMIT 80",
            table="relations",
        ):
            node_id = row["relation_id"]
            nodes[node_id] = _node(
                node_id,
                row.get("custom_label") or row.get("summary") or row.get("core_type") or node_id,
                "relation",
                active=False,
                data={**row, "metadata_json": _json_loads(row.get("metadata_json"))},
            )

        for row in _select_rows(
            conn,
            "SELECT * FROM groups WHERE status='active' ORDER BY name, group_id LIMIT 50",
            table="groups",
        ):
            node_id = row["group_id"]
            nodes[node_id] = _node(
                node_id,
                row.get("name") or row.get("summary") or node_id,
                "group",
                scene_id=scene_id if node_id in active_scene_groups else None,
                active=node_id in active_scene_groups,
                data=row,
            )

        for row in _select_rows(
            conn,
            "SELECT * FROM scenes WHERE status='active' ORDER BY updated_at DESC, created_at DESC, scene_id LIMIT 50",
            table="scenes",
        ):
            node_id = row["scene_id"]
            nodes[node_id] = _node(
                node_id,
                row.get("scene_summary") or node_id,
                "scene",
                scene_id=node_id,
                active=not scene_id or scene_id == node_id,
                data=row,
            )

        for row in _select_rows(
            conn,
            "SELECT * FROM states ORDER BY state_id LIMIT 80",
            table="states",
        ):
            node_id = row["state_id"]
            state_type = row.get("state_type") or "state"
            nodes[node_id] = _node(
                node_id,
                f"{state_type}: {row.get('scope_id') or node_id}",
                "state",
                active=row.get("scope_id") in active_scene_people,
                data={**row, "value_json": _json_loads(row.get("value_json"))},
            )

        for row in _select_rows(
            conn,
            "SELECT * FROM objects WHERE status='active' ORDER BY object_id LIMIT 50",
            table="objects",
        ):
            node_id = row["object_id"]
            nodes[node_id] = _node(
                node_id,
                row.get("name") or row.get("kind") or node_id,
                "object",
                active=False,
                data={**row, "metadata_json": _json_loads(row.get("metadata_json"))},
            )

        for row in _select_rows(
            conn,
            "SELECT * FROM places WHERE status='active' ORDER BY place_id LIMIT 50",
            table="places",
        ):
            node_id = row["place_id"]
            nodes[node_id] = _node(
                node_id,
                row.get("name") or row.get("scope") or node_id,
                "place",
                active=False,
                data={**row, "metadata_json": _json_loads(row.get("metadata_json"))},
            )

        for row in _select_rows(
            conn,
            "SELECT * FROM projects WHERE status='active' ORDER BY project_id LIMIT 50",
            table="projects",
        ):
            node_id = row["project_id"]
            nodes[node_id] = _node(
                node_id,
                row.get("name") or row.get("goal") or node_id,
                "project",
                active=False,
                data={**row, "metadata_json": _json_loads(row.get("metadata_json"))},
            )

        for row in _select_rows(
            conn,
            "SELECT scene_id, person_id, activation_state FROM scene_participants",
            table="scene_participants",
        ):
            if row["scene_id"] in nodes and row["person_id"] in nodes:
                edge_id = f"scene_participant:{row['scene_id']}:{row['person_id']}"
                edges[edge_id] = _edge(edge_id, row["scene_id"], row["person_id"], row.get("activation_state") or "participant", "scene_participant")

        for row in _select_rows(
            conn,
            "SELECT group_id, person_id, role_label FROM group_members WHERE status IS NULL OR status='active'",
            table="group_members",
        ):
            if row["group_id"] in nodes and row["person_id"] in nodes:
                edge_id = f"group_member:{row['group_id']}:{row['person_id']}"
                edges[edge_id] = _edge(edge_id, row["group_id"], row["person_id"], row.get("role_label") or "member", "group_member")

        for row in _select_rows(
            conn,
            "SELECT memory_id, owner_id, role_label FROM memory_owners WHERE owner_type='person'",
            table="memory_owners",
        ):
            if row["memory_id"] in nodes and row["owner_id"] in nodes:
                edge_id = f"memory_owner:{row['owner_id']}:{row['memory_id']}"
                edges[edge_id] = _edge(edge_id, row["owner_id"], row["memory_id"], row.get("role_label") or "remembers", "memory_owner")

        for row in _select_rows(
            conn,
            "SELECT from_id, relation_type, to_id FROM entity_links",
            table="entity_links",
        ):
            if row["from_id"] in nodes and row["to_id"] in nodes:
                edge_id = f"entity_link:{row['from_id']}:{row['relation_type']}:{row['to_id']}"
                edges[edge_id] = _edge(edge_id, row["from_id"], row["to_id"], row["relation_type"], "entity_link")

        for row in _select_rows(
            conn,
            "SELECT * FROM objects WHERE status='active'",
            table="objects",
        ):
            object_id = row.get("object_id")
            owner_id = row.get("owner_id")
            if object_id in nodes and owner_id in nodes:
                edge_id = f"object_owner:{owner_id}:{object_id}"
                edges[edge_id] = _edge(edge_id, owner_id, object_id, row.get("owner_type") or "owns", "object_owner")
            place_id = row.get("location_place_id")
            if object_id in nodes and place_id in nodes:
                edge_id = f"object_location:{object_id}:{place_id}"
                edges[edge_id] = _edge(edge_id, object_id, place_id, "located_at", "object_location")

        for row in _select_rows(
            conn,
            "SELECT from_id, to_id FROM entity_links WHERE from_type='project' AND to_type='person'",
            table="entity_links",
        ):
            if row["from_id"] in nodes and row["to_id"] in nodes:
                edge_id = f"project_involves:{row['from_id']}:{row['to_id']}"
                edges[edge_id] = _edge(edge_id, row["from_id"], row["to_id"], "involves", "project_involves")

        for row in _select_rows(
            conn,
            "SELECT state_id, scope_id, state_type FROM states",
            table="states",
        ):
            if row["state_id"] in nodes and row["scope_id"] in nodes:
                edge_id = f"state_scope:{row['scope_id']}:{row['state_id']}"
                edges[edge_id] = _edge(edge_id, row["scope_id"], row["state_id"], row.get("state_type") or "state", "state_scope")

        return {"source": "local_skill", "nodes": list(nodes.values()), "edges": list(edges.values())}
    finally:
        conn.close()


def list_local_events(*, root: Path, tenant_id: str | None, limit: int = 20) -> dict:
    db_path = _tenant_db_path(root, tenant_id)
    if not db_path.exists():
        return {"source": "local_skill", "events": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = _select_rows(
            conn,
            "SELECT * FROM events ORDER BY COALESCE(timestamp, created_at, event_id) DESC LIMIT ?",
            (limit,),
            table="events",
        )
        return {"source": "local_skill", "events": [_decode_payload_columns(row) for row in rows]}
    finally:
        conn.close()


def _decode_payload_columns(row: dict) -> dict:
    decoded = dict(row)
    for key in (
        "payload_json",
        "metadata_json",
        "raw_evidence_refs_json",
        "source_memory_ids_json",
        "source_event_ids_json",
        "value_json",
    ):
        if key in decoded:
            fallback = [] if key.endswith("refs_json") or key.startswith("source_") else {}
            decoded[key] = _json_loads(decoded[key], fallback)
    return decoded


def list_local_patches(*, root: Path, tenant_id: str | None, limit: int = 20) -> dict:
    db_path = _tenant_db_path(root, tenant_id)
    if not db_path.exists():
        return {"source": "local_skill", "patches": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = _select_rows(
            conn,
            "SELECT * FROM patches ORDER BY COALESCE(applied_at, created_at, patch_id) DESC LIMIT ?",
            (limit,),
            table="patches",
        )
        return {"source": "local_skill", "patches": [_decode_payload_columns(row) for row in rows]}
    finally:
        conn.close()


def list_local_snapshots(*, root: Path, tenant_id: str | None, limit: int = 20) -> dict:
    db_path = _tenant_db_path(root, tenant_id)
    if not db_path.exists():
        return {"source": "local_skill", "snapshots": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = _select_rows(
            conn,
            "SELECT * FROM snapshots ORDER BY COALESCE(created_at, snapshot_id) DESC LIMIT ?",
            (limit,),
            table="snapshots",
        )
        return {"source": "local_skill", "snapshots": rows}
    finally:
        conn.close()


def list_local_branches(*, root: Path, tenant_id: str | None, status: str = "open") -> dict:
    db_path = _tenant_db_path(root, tenant_id)
    if not db_path.exists():
        return {"source": "local_skill", "branches": []}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        branches = _select_rows(
            conn,
            "SELECT * FROM local_branches WHERE status = ? ORDER BY created_at DESC, branch_id",
            (status,),
            table="local_branches",
        )
        if not branches:
            return {"source": "local_skill", "branches": []}
        branch_ids = [branch["branch_id"] for branch in branches]
        candidates_by_branch: dict[str, list[dict]] = {branch_id: [] for branch_id in branch_ids}
        if _table_exists(conn, "branch_candidates"):
            placeholders = ",".join("?" for _ in branch_ids)
            rows = conn.execute(
                f"SELECT * FROM branch_candidates WHERE branch_id IN ({placeholders}) "
                "ORDER BY COALESCE(confidence, 0) DESC, candidate_id",
                tuple(branch_ids),
            ).fetchall()
            for row in rows:
                candidate = _decode_payload_columns(dict(row))
                candidates_by_branch.setdefault(candidate["branch_id"], []).append(candidate)
        for branch in branches:
            branch["candidates"] = candidates_by_branch.get(branch["branch_id"], [])
        return {"source": "local_skill", "branches": branches}
    finally:
        conn.close()


def _list_table_rows(conn: sqlite3.Connection, table: str, query: str, params: tuple = ()) -> list[dict]:
    return [_decode_payload_columns(row) for row in _select_rows(conn, query, params, table=table)]


def build_local_world(*, root: Path, tenant_id: str | None, scene_id: str | None = None) -> dict:
    db_path = _tenant_db_path(root, tenant_id)
    if not db_path.exists():
        return {
            "source": "local_skill",
            "participants": [],
            "objects": [],
            "places": [],
            "projects": [],
            "agent_drives": [],
            "autonomous_actions": [],
        }
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    participants: list[str] = []
    try:
        if scene_id and _table_exists(conn, "scene_participants"):
            participants = [
                row["person_id"]
                for row in conn.execute("SELECT person_id FROM scene_participants WHERE scene_id = ?", (scene_id,)).fetchall()
            ]
        world = {
            "participants": participants,
            "objects": [],
            "places": [],
            "projects": [],
            "agent_drives": [],
            "autonomous_actions": [],
        }
        if scene_id and _table_exists(conn, "objects") and _table_exists(conn, "places") and _table_exists(conn, "projects"):
            try:
                scene_world = active_world_for_scene(db_path, scene_id)
                world.update({
                    "participants": scene_world.get("participants", participants),
                    "objects": scene_world.get("objects", []),
                    "places": scene_world.get("places", []),
                    "projects": scene_world.get("projects", []),
                })
            except sqlite3.Error:
                pass
        if not world["objects"]:
            world["objects"] = _list_table_rows(
                conn,
                "objects",
                "SELECT * FROM objects WHERE status='active' ORDER BY object_id LIMIT 50",
            )
        if not world["places"]:
            world["places"] = _list_table_rows(
                conn,
                "places",
                "SELECT * FROM places WHERE status='active' ORDER BY place_id LIMIT 50",
            )
        if not world["projects"]:
            world["projects"] = _list_table_rows(
                conn,
                "projects",
                "SELECT * FROM projects WHERE status='active' ORDER BY project_id LIMIT 50",
            )
        if _table_exists(conn, "agent_drives"):
            if participants:
                placeholders = ",".join("?" for _ in participants)
                world["agent_drives"] = _list_table_rows(
                    conn,
                    "agent_drives",
                    f"SELECT * FROM agent_drives WHERE status='active' AND person_id IN ({placeholders}) "
                    "ORDER BY activated_at DESC, drive_id LIMIT 50",
                    tuple(participants),
                )
            if not world["agent_drives"]:
                world["agent_drives"] = _list_table_rows(
                    conn,
                    "agent_drives",
                    "SELECT * FROM agent_drives WHERE status='active' ORDER BY activated_at DESC, drive_id LIMIT 50",
                )
        if _table_exists(conn, "autonomous_actions"):
            if participants:
                placeholders = ",".join("?" for _ in participants)
                world["autonomous_actions"] = _list_table_rows(
                    conn,
                    "autonomous_actions",
                    f"SELECT * FROM autonomous_actions WHERE person_id IN ({placeholders}) "
                    "ORDER BY created_at DESC, action_id DESC LIMIT 50",
                    tuple(participants),
                )
            if not world["autonomous_actions"]:
                world["autonomous_actions"] = _list_table_rows(
                    conn,
                    "autonomous_actions",
                    "SELECT * FROM autonomous_actions ORDER BY created_at DESC, action_id DESC LIMIT 50",
                )
        return {"source": "local_skill", **world}
    finally:
        conn.close()


def bootstrap_local_runtime(*, root: Path, tenant_id: str | None) -> dict:
    tenant_root = _tenant_root(root, tenant_id)
    bootstrap_project(tenant_root)
    return {
        "source": "local_skill",
        "tenant_id": infer_tenant_id_from_root(tenant_root),
        "tenant_root": str(tenant_root),
        "db_path": str(tenant_root / "db" / "main.sqlite3"),
    }


def seed_local_demo(*, root: Path, tenant_id: str | None) -> dict:
    bootstrap = bootstrap_local_runtime(root=root, tenant_id=tenant_id)
    tenant_root = _tenant_root(root, tenant_id)
    return {"source": "local_skill", "bootstrap": bootstrap, "seed": seed_society_c(tenant_root)}


def import_local_narration(*, root: Path, tenant_id: str | None, payload: dict) -> dict:
    text = str(payload.get("text") or "").strip()
    if not text:
        raise ValueError("text is required")
    source_name = str(payload.get("source_name") or "webui-narration").strip() or "webui-narration"
    bootstrap = bootstrap_local_runtime(root=root, tenant_id=tenant_id)
    tenant_root = _tenant_root(root, tenant_id)
    scene_id = str(payload.get("scene_id") or "").strip() or None
    result = ingest_narration(
        tenant_root / "db" / "main.sqlite3",
        text,
        source_name,
        scene_id=scene_id,
    )
    return {"source": "local_skill", "bootstrap": bootstrap, "result": result}


def resolve_local_branch(*, root: Path, tenant_id: str | None, branch_id: str, payload: dict) -> dict:
    candidate_id = str(payload.get("candidate_id") or "").strip()
    if not candidate_id:
        raise ValueError("candidate_id is required")
    reason = str(payload.get("reason") or "operator approved via WebUI").strip()
    tenant_root = _tenant_root(root, tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    patch = build_patch(
        source_event_id=f"webui_resolve_{branch_id}",
        target_type="local_branch",
        target_id=branch_id,
        operation="resolve_local_branch",
        payload={
            "branch_id": branch_id,
            "selected_candidate_id": candidate_id,
            "reason": reason,
            "status": "resolved",
        },
        confidence=float(payload.get("confidence", 1.0)),
        reason=reason,
    )
    apply_patch_record(db_path=db_path, patch=patch)
    return {
        "source": "local_skill",
        "branch_id": branch_id,
        "selected_candidate_id": candidate_id,
        "patch_id": patch["patch_id"],
        "status": "resolved",
    }


def build_runtime_status(
    *,
    root: Path,
    tenant_id: str | None,
    provider: str | None,
    adapter: str,
) -> dict:
    base_root = Path(root).resolve()
    tenant_root = _tenant_root(base_root, tenant_id)
    return {
        "mode": "local_skill",
        "token_required": False,
        "provider": _resolved_provider_name(provider),
        "adapter": adapter,
        "tenant_id": infer_tenant_id_from_root(tenant_root),
        "root": str(base_root),
        "tenant_root": str(tenant_root),
        "db_path": str(tenant_root / "db" / "main.sqlite3"),
    }


def run_local_chat_turn(
    *,
    root: Path,
    tenant_id: str | None,
    provider: str | None,
    adapter: str,
    payload: dict,
) -> dict:
    scene_id = str(payload.get("scene_id") or "").strip()
    user_input = str(payload.get("input") or "").strip()
    if not scene_id:
        raise ValueError("scene_id is required")
    if not user_input:
        raise ValueError("input is required")

    tenant_root = _tenant_root(Path(root), tenant_id)
    llm_client = get_llm_client(provider)
    result = run_turn(
        db_path=tenant_root / "db" / "main.sqlite3",
        scene_id=scene_id,
        user_input=user_input,
        llm_client=llm_client,
        adapter_name=adapter,
        history=payload.get("history") if isinstance(payload.get("history"), list) else None,
        speaking_person_ids=payload.get("speaking_person_ids")
        if isinstance(payload.get("speaking_person_ids"), list)
        else None,
        max_recent_changes=payload.get("max_recent_changes", 5),
    )
    return {
        "mode": "local_skill",
        "token_required": False,
        "provider": getattr(llm_client, "provider", _resolved_provider_name(provider)),
        "adapter": adapter,
        "tenant_id": infer_tenant_id_from_root(tenant_root),
        "text": _response_text(result),
        "event_id": result.get("event_id"),
        "snapshot_id": result.get("snapshot_id"),
        "applied_patch_count": result.get("applied_patch_count", 0),
        "speaker_person_id": (result.get("response") or {}).get("speaker_person_id"),
        "retrieval_package": (result.get("request") or {}).get("retrieval_package"),
        "raw": result,
    }


def make_handler(config: BridgeConfig):
    class WebUIBridgeHandler(BaseHTTPRequestHandler):
        server_version = "WeTogetherWebUIBridge/0.1"

        def _write_json(self, status: int, payload: dict, *, include_body: bool = True) -> None:
            body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body) if include_body else 0))
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5173")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, HEAD, POST, OPTIONS")
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            if not raw:
                return {}
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON body: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            return payload

        def do_HEAD(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/runtime/status":
                self._write_json(
                    200,
                    {"ok": True, "data": build_runtime_status(**config.__dict__)},
                    include_body=False,
                )
            else:
                self._write_json(404, {"ok": False, "error": {"message": "not found"}}, include_body=False)

        def do_OPTIONS(self) -> None:
            self._write_json(204, {}, include_body=False)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            if path == "/api/runtime/status":
                self._write_json(200, {"ok": True, "data": build_runtime_status(**config.__dict__)})
                return
            if path == "/api/scenes":
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "data": list_local_scenes(root=config.root, tenant_id=config.tenant_id),
                    },
                )
                return
            if path == "/api/graph":
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "data": build_local_graph(
                            root=config.root,
                            tenant_id=config.tenant_id,
                            scene_id=(query.get("scene_id") or [None])[0],
                        ),
                    },
                )
                return
            if path == "/api/events":
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "data": list_local_events(
                            root=config.root,
                            tenant_id=config.tenant_id,
                            limit=int((query.get("limit") or ["20"])[0]),
                        ),
                    },
                )
                return
            if path == "/api/patches":
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "data": list_local_patches(
                            root=config.root,
                            tenant_id=config.tenant_id,
                            limit=int((query.get("limit") or ["20"])[0]),
                        ),
                    },
                )
                return
            if path == "/api/snapshots":
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "data": list_local_snapshots(
                            root=config.root,
                            tenant_id=config.tenant_id,
                            limit=int((query.get("limit") or ["20"])[0]),
                        ),
                    },
                )
                return
            if path == "/api/branches":
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "data": list_local_branches(
                            root=config.root,
                            tenant_id=config.tenant_id,
                            status=(query.get("status") or ["open"])[0],
                        ),
                    },
                )
                return
            if path == "/api/world":
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "data": build_local_world(
                            root=config.root,
                            tenant_id=config.tenant_id,
                            scene_id=(query.get("scene_id") or [None])[0],
                        ),
                    },
                )
                return
            if path == "/api/summary":
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "data": build_local_summary(root=config.root, tenant_id=config.tenant_id),
                    },
                )
                return
            self._write_json(404, {"ok": False, "error": {"message": "not found"}})

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._write_json(400, {"ok": False, "error": {"message": str(exc)}})
                return
            try:
                if path == "/api/bootstrap":
                    self._write_json(200, {"ok": True, "data": bootstrap_local_runtime(root=config.root, tenant_id=config.tenant_id)})
                    return
                if path == "/api/seed-demo":
                    self._write_json(200, {"ok": True, "data": seed_local_demo(root=config.root, tenant_id=config.tenant_id)})
                    return
                if path == "/api/import/narration":
                    self._write_json(
                        200,
                        {
                            "ok": True,
                            "data": import_local_narration(root=config.root, tenant_id=config.tenant_id, payload=payload),
                        },
                    )
                    return
                if path.startswith("/api/branches/") and path.endswith("/resolve"):
                    branch_id = path.removeprefix("/api/branches/").removesuffix("/resolve").strip("/")
                    self._write_json(
                        200,
                        {
                            "ok": True,
                            "data": resolve_local_branch(
                                root=config.root,
                                tenant_id=config.tenant_id,
                                branch_id=branch_id,
                                payload=payload,
                            ),
                        },
                    )
                    return
                if path == "/api/chat/run-turn":
                    self._write_json(
                        200,
                        {"ok": True, "data": run_local_chat_turn(payload=payload, **config.__dict__)},
                    )
                    return
            except ValueError as exc:
                self._write_json(400, {"ok": False, "error": {"message": str(exc)}})
                return
            except Exception as exc:
                self._write_json(500, {"ok": False, "error": {"message": str(exc)}})
                return
            if path != "/api/chat/run-turn":
                self._write_json(404, {"ok": False, "error": {"message": "not found"}})
                return

        def log_message(self, *_args) -> None:
            return

    return WebUIBridgeHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local WebUI skill bridge.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--adapter", default="claude", choices=["claude", "openai", "openai_compat"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("WEBUI_LOCAL_BRIDGE_PORT", "7781")))
    args = parser.parse_args(argv)

    config = BridgeConfig(
        root=Path(args.root).resolve(),
        tenant_id=args.tenant_id,
        provider=args.provider,
        adapter=args.adapter,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(config))
    print(
        f"we-together WebUI bridge listening on http://{args.host}:{args.port} "
        f"| provider={_resolved_provider_name(args.provider)} adapter={args.adapter}",
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
