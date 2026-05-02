"""we-together MCP server (stdio, JSON-RPC 2.0)。

Phase 33 扩展（v0.14.0 / ADR 0035）：支持 initialize / tools / resources / prompts 全套。

协议子集:
  - initialize
  - tools/list, tools/call
  - resources/list, resources/read
  - prompts/list, prompts/get

Claude Code 接入:
  claude mcp add we-together -- python /abs/path/scripts/mcp_server.py --root /abs/data
"""
from __future__ import annotations

import argparse
import io
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from we_together.llm import get_llm_client
from we_together import __version__ as WE_TOGETHER_VERSION
from we_together.runtime.adapters.mcp_adapter import (
    build_mcp_prompts,
    build_mcp_resources,
    build_mcp_tools,
)
from we_together.runtime.skill_runtime import SKILL_SCHEMA_VERSION
from we_together.services.chat_service import run_turn
from we_together.services.tenant_router import infer_tenant_id_from_root, resolve_tenant_root

SERVER_VERSION = WE_TOGETHER_VERSION


def _db_path_for_root(root: Path) -> Path:
    return root / "db" / "main.sqlite3"


def _runtime_context(root: Path, db_path: Path | None = None) -> dict:
    db_path = db_path or _db_path_for_root(root)
    return {
        "source": "local_skill",
        "tenant_id": infer_tenant_id_from_root(root),
        "tenant_root": str(root),
        "db_path": str(db_path),
    }


def _graph_summary(root: Path) -> dict:
    db_path = _db_path_for_root(root)
    if not db_path.exists():
        return {**_runtime_context(root, db_path), "error": "db not found"}
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT (SELECT COUNT(*) FROM persons WHERE status='active'), "
        "(SELECT COUNT(*) FROM relations WHERE status='active'), "
        "(SELECT COUNT(*) FROM scenes WHERE status='active'), "
        "(SELECT COUNT(*) FROM events), "
        "(SELECT COUNT(*) FROM memories WHERE status='active')"
    ).fetchone()
    conn.close()
    return {
        **_runtime_context(root, db_path),
        "person_count": row[0], "relation_count": row[1], "scene_count": row[2],
        "event_count": row[3], "memory_count": row[4],
    }


def _scene_list(root: Path) -> dict:
    db_path = _db_path_for_root(root)
    if not db_path.exists():
        return {**_runtime_context(root, db_path), "error": "db not found"}
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT s.scene_id, s.scene_type, s.status, "
        "(SELECT COUNT(*) FROM scene_participants WHERE scene_id=s.scene_id) "
        "FROM scenes s WHERE s.status='active' LIMIT 50"
    ).fetchall()
    conn.close()
    return {**_runtime_context(root, db_path), "scenes": [
        {"scene_id": r[0], "scene_type": r[1], "status": r[2], "participants": r[3]}
        for r in rows
    ]}


def _snapshot_list(root: Path, limit: int = 10) -> dict:
    db_path = _db_path_for_root(root)
    if not db_path.exists():
        return {**_runtime_context(root, db_path), "error": "db not found"}
    from we_together.services.snapshot_service import list_snapshots

    return {
        **_runtime_context(root, db_path),
        "snapshots": list_snapshots(db_path, limit=int(limit)),
    }


def _proactive_scan(root: Path, daily_budget: int = 3) -> dict:
    from we_together.services.proactive_agent import scan_all_triggers
    db_path = root / "db" / "main.sqlite3"
    if not db_path.exists():
        return {"error": "db not found"}
    triggers = scan_all_triggers(db_path)
    return {"trigger_count": len(triggers), "triggers": [
        {"name": t.name, "metadata": t.metadata} for t in triggers[:daily_budget]
    ]}


def _make_dispatcher(root: Path):
    from we_together.services.self_introspection import (
        check_invariant,
        list_invariants,
        self_describe,
    )

    def we_together_graph_summary(args: dict) -> dict:
        return _graph_summary(root)

    def we_together_run_turn(args: dict) -> dict:
        scene_id = args.get("scene_id", "")
        text = args.get("input", "")
        if not scene_id or not text:
            return {"error": "scene_id and input required"}
        db_path = _db_path_for_root(root)
        llm_client = get_llm_client()
        result = run_turn(
            db_path=db_path, scene_id=scene_id, user_input=text,
            llm_client=llm_client,
            adapter_name="openai_compat",
        )
        response = result.get("response") or {}
        return {
            **_runtime_context(root, db_path),
            "text": response.get("text", ""),
            "event_id": result.get("event_id"),
            "snapshot_id": result.get("snapshot_id"),
            "applied_patch_count": result.get("applied_patch_count", 0),
            "provider": getattr(llm_client, "provider", None),
        }

    def we_together_scene_list(args: dict) -> dict:
        return _scene_list(root)

    def we_together_snapshot_list(args: dict) -> dict:
        return _snapshot_list(root, limit=int(args.get("limit", 10)))

    def we_together_import_narration(args: dict) -> dict:
        from we_together.services.ingestion_service import ingest_narration
        scene_id = args.get("scene_id", "")
        text = args.get("text", "")
        source = args.get("source_person_id")
        if not scene_id or not text:
            return {"error": "scene_id and text required"}
        db_path = _db_path_for_root(root)
        r = ingest_narration(
            db_path=db_path,
            text=text,
            source_name=source or "mcp-narration",
            scene_id=scene_id,
        )
        return {
            **_runtime_context(root, db_path),
            "event_id": r.get("event_id"),
            "snapshot_id": r.get("snapshot_id"),
            "patch_id": r.get("patch_id"),
            "patch_count": 1 if r.get("patch_id") else 0,
            "person_ids": r.get("person_ids", []),
        }

    def we_together_proactive_scan(args: dict) -> dict:
        return _proactive_scan(root, daily_budget=int(args.get("daily_budget", 3)))

    def we_together_self_describe(args: dict) -> dict:
        return self_describe()

    def we_together_list_invariants(args: dict) -> dict:
        return {"invariants": list_invariants()}

    def we_together_check_invariant(args: dict) -> dict:
        return check_invariant(int(args.get("invariant_id")))

    return {
        "we_together_graph_summary": we_together_graph_summary,
        "we_together_run_turn": we_together_run_turn,
        "we_together_scene_list": we_together_scene_list,
        "we_together_snapshot_list": we_together_snapshot_list,
        "we_together_import_narration": we_together_import_narration,
        "we_together_proactive_scan": we_together_proactive_scan,
        "we_together_self_describe": we_together_self_describe,
        "we_together_list_invariants": we_together_list_invariants,
        "we_together_check_invariant": we_together_check_invariant,
    }


def _read_resource(uri: str, root: Path) -> dict:
    if uri == "we-together://graph/summary":
        content = json.dumps(_graph_summary(root), ensure_ascii=False)
        return {"uri": uri, "mimeType": "application/json", "text": content}
    if uri == "we-together://schema/version":
        return {"uri": uri, "mimeType": "text/plain", "text": SKILL_SCHEMA_VERSION}
    raise ValueError(f"unknown resource: {uri}")


def _get_prompt(name: str, args: dict) -> dict:
    if name == "we_together_scene_reply":
        scene_id = args.get("scene_id", "")
        user_input = args.get("user_input", "")
        return {
            "description": "Scene-grounded reply",
            "messages": [
                {
                    "role": "assistant",
                    "content": {
                        "type": "text",
                        "text": (
                            "You are an agent inside a we-together social graph. "
                            f"Reply in scene {scene_id}, grounded in retrieval package."
                        ),
                    },
                },
                {"role": "user", "content": {"type": "text", "text": user_input}},
            ],
        }
    raise ValueError(f"unknown prompt: {name}")


def handle_request(
    req: dict, *, dispatcher: dict, tools: list[dict],
    resources: list[dict] | None = None, prompts: list[dict] | None = None,
    root: Path | None = None,
) -> dict | None:
    resources = resources if resources is not None else []
    prompts = prompts if prompts is not None else []
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params") or {}

    if req_id is None and method and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "we-together", "version": SERVER_VERSION},
                "capabilities": {
                    "tools": {},
                    "resources": {},
                    "prompts": {},
                },
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in dispatcher:
            return {"jsonrpc": "2.0", "id": req_id,
                     "error": {"code": -32601, "message": f"unknown tool: {name}"}}
        try:
            result = dispatcher[name](args)
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": req_id,
                     "error": {"code": -32000, "message": str(exc)}}
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "content": [{"type": "text",
                              "text": json.dumps(result, ensure_ascii=False)}],
                "isError": False,
            },
        }
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": resources}}
    if method == "resources/read":
        uri = params.get("uri", "")
        try:
            content = _read_resource(uri, root)
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": req_id,
                     "error": {"code": -32000, "message": str(exc)}}
        return {"jsonrpc": "2.0", "id": req_id,
                 "result": {"contents": [content]}}
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": prompts}}
    if method == "prompts/get":
        name = params.get("name", "")
        try:
            prompt = _get_prompt(name, params.get("arguments") or {})
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": req_id,
                     "error": {"code": -32000, "message": str(exc)}}
        return {"jsonrpc": "2.0", "id": req_id, "result": prompt}
    return {"jsonrpc": "2.0", "id": req_id,
             "error": {"code": -32601, "message": f"unknown method: {method}"}}


def _read_stdio_message(stream) -> tuple[dict, str] | tuple[None, None]:
    while True:
        first_line = stream.readline()
        if first_line in {"", b""}:
            return None, None
        first_line_text = (
            first_line.decode("utf-8", errors="replace")
            if isinstance(first_line, bytes)
            else first_line
        )
        if first_line_text.strip():
            break

    if first_line_text.lower().startswith("content-length:"):
        length = None
        try:
            length = int(first_line_text.split(":", 1)[1].strip())
        except ValueError:
            return None, None

        while True:
            line = stream.readline()
            if line in {"", b""}:
                return None, None
            line_text = (
                line.decode("utf-8", errors="replace")
                if isinstance(line, bytes)
                else line
            )
            if line_text in {"\n", "\r\n"}:
                break
            if line_text.lower().startswith("content-length:"):
                try:
                    length = int(line_text.split(":", 1)[1].strip())
                except ValueError:
                    return None, None

        body = stream.read(length)
        if not body:
            return None, None
        body_text = (
            body.decode("utf-8", errors="replace")
            if isinstance(body, bytes)
            else body
        )
        return json.loads(body_text), "framed"

    return json.loads(first_line_text.strip()), "line"


def _write_stdio_message(stream, payload: dict, mode: str) -> None:
    body = json.dumps(payload, ensure_ascii=False)
    body_bytes = body.encode("utf-8")
    if mode == "framed":
        framed = f"Content-Length: {len(body_bytes)}\r\n\r\n".encode() + body_bytes
        if isinstance(stream, io.TextIOBase):
            stream.write(framed.decode("utf-8"))
        else:
            stream.write(framed)
    else:
        if isinstance(stream, io.TextIOBase):
            stream.write(body + "\n")
        else:
            stream.write(body_bytes + b"\n")
    stream.flush()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--tenant-id", default=None)
    args = ap.parse_args()
    root = resolve_tenant_root(Path(args.root).resolve(), args.tenant_id)
    tools = build_mcp_tools()
    resources = build_mcp_resources()
    prompts = build_mcp_prompts()
    dispatcher = _make_dispatcher(root)

    stdin_stream = getattr(sys.stdin, "buffer", sys.stdin)
    stdout_stream = getattr(sys.stdout, "buffer", sys.stdout)

    while True:
        try:
            req, mode = _read_stdio_message(stdin_stream)
        except json.JSONDecodeError:
            continue
        if req is None:
            break
        resp = handle_request(
            req, dispatcher=dispatcher, tools=tools,
            resources=resources, prompts=prompts, root=root,
        )
        if resp is not None:
            _write_stdio_message(stdout_stream, resp, mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
