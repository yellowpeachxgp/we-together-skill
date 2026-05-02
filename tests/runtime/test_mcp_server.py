import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from mcp_server import handle_request  # noqa: E402

from we_together.runtime.adapters.mcp_adapter import build_mcp_tools  # noqa: E402


def test_initialize():
    from we_together import __version__  # noqa: E402

    r = handle_request(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
        dispatcher={}, tools=[],
    )
    assert r["id"] == 1
    assert r["result"]["serverInfo"]["name"] == "we-together"
    assert r["result"]["serverInfo"]["version"] == __version__


def test_tools_list_returns_we_together_tools():
    tools = build_mcp_tools()
    r = handle_request(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        dispatcher={}, tools=tools,
    )
    names = {t["name"] for t in r["result"]["tools"]}
    assert "we_together_run_turn" in names
    assert "we_together_graph_summary" in names


def test_tools_call_dispatches():
    calls = []
    def _handler(args):
        calls.append(args)
        return {"ok": True}
    r = handle_request(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "we_together_graph_summary",
                     "arguments": {"scene_id": "s1"}}},
        dispatcher={"we_together_graph_summary": _handler},
        tools=build_mcp_tools(),
    )
    assert r["result"]["isError"] is False
    payload = json.loads(r["result"]["content"][0]["text"])
    assert payload == {"ok": True}
    assert calls[0] == {"scene_id": "s1"}


def test_tools_call_unknown_tool():
    r = handle_request(
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
         "params": {"name": "not_there", "arguments": {}}},
        dispatcher={}, tools=[],
    )
    assert "error" in r
    assert r["error"]["code"] == -32601


def test_snapshot_list_uses_current_snapshot_schema(temp_project_with_migrations):
    from mcp_server import _make_dispatcher  # noqa: E402
    from we_together.db.bootstrap import bootstrap_project  # noqa: E402
    from we_together.services.dialogue_service import record_dialogue_event  # noqa: E402
    from we_together.services.scene_service import create_scene  # noqa: E402

    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="mcp snapshot schema regression",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    event_result = record_dialogue_event(
        db_path=db_path,
        scene_id=scene_id,
        user_input="checkpoint",
        response_text="ok",
        speaking_person_ids=[],
    )

    dispatcher = _make_dispatcher(temp_project_with_migrations)
    result = dispatcher["we_together_snapshot_list"]({"limit": 5})

    assert result["source"] == "local_skill"
    assert result["tenant_id"] == "default"
    assert result["db_path"].endswith("/db/main.sqlite3")
    assert result["snapshots"][0]["snapshot_id"] == event_result["snapshot_id"]
    assert result["snapshots"][0]["trigger_event_id"] == event_result["event_id"]
    assert "scene_id" not in result["snapshots"][0]


def test_run_turn_tool_returns_response_text_and_event_id(temp_project_with_migrations, monkeypatch):
    from mcp_server import _make_dispatcher  # noqa: E402
    from we_together.db.bootstrap import bootstrap_project  # noqa: E402
    from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
    from we_together.services.scene_service import create_scene  # noqa: E402

    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="mcp run turn regression",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )

    monkeypatch.setattr(
        "mcp_server.get_llm_client",
        lambda: MockLLMClient(default_content="mcp response ok"),
    )
    dispatcher = _make_dispatcher(temp_project_with_migrations)
    result = dispatcher["we_together_run_turn"](
        {"scene_id": scene_id, "input": "hello"}
    )

    assert result["text"] == "mcp response ok"
    assert result["event_id"].startswith("evt_")
    assert result["snapshot_id"].startswith("snap_")
    assert result["applied_patch_count"] >= 1
    assert result["provider"] == "mock"


def test_import_narration_tool_uses_real_ingestion_service(temp_project_with_migrations):
    from mcp_server import _make_dispatcher  # noqa: E402
    from we_together.db.bootstrap import bootstrap_project  # noqa: E402
    from we_together.services.scene_service import create_scene  # noqa: E402

    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="mcp import narration regression",
        environment={
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
        },
    )
    dispatcher = _make_dispatcher(temp_project_with_migrations)

    result = dispatcher["we_together_import_narration"](
        {"scene_id": scene_id, "text": "小明和小强是朋友", "source_person_id": "p_source"}
    )

    assert result["source"] == "local_skill"
    assert result["tenant_id"] == "default"
    assert result["event_id"].startswith("evt_")
    assert result["snapshot_id"].startswith("snap_")
    assert result["patch_count"] >= 1

    conn = __import__("sqlite3").connect(db_path)
    try:
        event_scene_id = conn.execute(
            "SELECT scene_id FROM events WHERE event_id = ?",
            (result["event_id"],),
        ).fetchone()[0]
        snapshot_scene = conn.execute(
            "SELECT 1 FROM snapshot_entities WHERE snapshot_id = ? AND entity_type = 'scene' AND entity_id = ?",
            (result["snapshot_id"], scene_id),
        ).fetchone()
    finally:
        conn.close()
    assert event_scene_id == scene_id
    assert snapshot_scene is not None


def test_unknown_method():
    r = handle_request(
        {"jsonrpc": "2.0", "id": 5, "method": "xxx"},
        dispatcher={}, tools=[],
    )
    assert "error" in r


def test_initialized_notification_returns_no_response():
    r = handle_request(
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
        dispatcher={}, tools=[],
    )
    assert r is None
