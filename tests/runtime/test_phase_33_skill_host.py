"""Phase 33 — 真 Skill 宿主落地（SP slices）。

覆盖:
- SkillRequest/Response v1 schema_version (SP-10/11)
- MCP adapter tools/resources/prompts 扩展 (SP-6/7/8)
- MCP server handle_request 全套 (SP-9/17)
- package_skill.py 真打 zip + unpack roundtrip (SP-13)
- Claude + OpenAI adapter 双路径等价 (SP-12)
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def test_skill_request_roundtrip():
    from we_together.runtime.skill_runtime import SKILL_SCHEMA_VERSION, SkillRequest
    r = SkillRequest(
        system_prompt="sys", messages=[{"role": "user", "content": "hi"}],
        retrieval_package={"x": 1}, scene_id="s1", user_input="hi",
    )
    d = r.to_dict()
    assert d["schema_version"] == SKILL_SCHEMA_VERSION
    r2 = SkillRequest.from_dict(d)
    assert r2.scene_id == "s1"
    assert r2.schema_version == SKILL_SCHEMA_VERSION


def test_skill_response_roundtrip():
    from we_together.runtime.skill_runtime import SKILL_SCHEMA_VERSION, SkillResponse
    r = SkillResponse(text="hello", speaker_person_id="p1")
    d = r.to_dict()
    assert d["schema_version"] == SKILL_SCHEMA_VERSION
    r2 = SkillResponse.from_dict(d)
    assert r2.text == "hello" and r2.speaker_person_id == "p1"


def test_skill_request_rejects_wrong_version():
    import pytest

    from we_together.runtime.skill_runtime import SkillRequest
    with pytest.raises(ValueError, match="schema_version"):
        SkillRequest.from_dict({
            "schema_version": "99",
            "system_prompt": "", "messages": [], "retrieval_package": {},
            "scene_id": "", "user_input": "",
        })


def test_mcp_adapter_exposes_tools():
    from we_together.runtime.adapters.mcp_adapter import build_mcp_tools
    tools = build_mcp_tools()
    names = {t["name"] for t in tools}
    # Phase 33 扩展后至少包含 6 个工具
    assert {"we_together_run_turn", "we_together_graph_summary",
            "we_together_scene_list", "we_together_snapshot_list",
            "we_together_import_narration",
            "we_together_proactive_scan"} <= names


def test_mcp_adapter_exposes_resources():
    from we_together.runtime.adapters.mcp_adapter import build_mcp_resources
    rs = build_mcp_resources()
    uris = {r["uri"] for r in rs}
    assert "we-together://graph/summary" in uris
    assert "we-together://schema/version" in uris


def test_mcp_adapter_exposes_prompts():
    from we_together.runtime.adapters.mcp_adapter import build_mcp_prompts
    ps = build_mcp_prompts()
    assert any(p["name"] == "we_together_scene_reply" for p in ps)


def test_mcp_server_initialize(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    import mcp_server
    tools = mcp_server.build_mcp_tools()
    resources = mcp_server.build_mcp_resources()
    prompts = mcp_server.build_mcp_prompts()
    dispatcher = mcp_server._make_dispatcher(temp_project_with_migrations)
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    resp = mcp_server.handle_request(
        req, dispatcher=dispatcher, tools=tools,
        resources=resources, prompts=prompts, root=temp_project_with_migrations,
    )
    assert resp["result"]["serverInfo"]["name"] == "we-together"
    assert "resources" in resp["result"]["capabilities"]
    assert "prompts" in resp["result"]["capabilities"]


def test_mcp_server_tools_list_and_call(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    import mcp_server
    tools = mcp_server.build_mcp_tools()
    resources = mcp_server.build_mcp_resources()
    prompts = mcp_server.build_mcp_prompts()
    dispatcher = mcp_server._make_dispatcher(temp_project_with_migrations)

    req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    resp = mcp_server.handle_request(
        req, dispatcher=dispatcher, tools=tools,
        resources=resources, prompts=prompts, root=temp_project_with_migrations,
    )
    names = {t["name"] for t in resp["result"]["tools"]}
    assert "we_together_graph_summary" in names

    req2 = {
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "we_together_graph_summary", "arguments": {}},
    }
    resp2 = mcp_server.handle_request(
        req2, dispatcher=dispatcher, tools=tools,
        resources=resources, prompts=prompts, root=temp_project_with_migrations,
    )
    content = resp2["result"]["content"][0]
    assert content["type"] == "text"
    payload = json.loads(content["text"])
    assert "person_count" in payload
    assert payload["tenant_id"] == "default"


def test_mcp_server_self_introspection_tools_call(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    import mcp_server
    tools = mcp_server.build_mcp_tools()
    resources = mcp_server.build_mcp_resources()
    prompts = mcp_server.build_mcp_prompts()
    dispatcher = mcp_server._make_dispatcher(temp_project_with_migrations)

    for tool_name, arguments in [
        ("we_together_self_describe", {}),
        ("we_together_list_invariants", {}),
        ("we_together_check_invariant", {"invariant_id": 1}),
    ]:
        req = {
            "jsonrpc": "2.0",
            "id": tool_name,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        resp = mcp_server.handle_request(
            req,
            dispatcher=dispatcher,
            tools=tools,
            resources=resources,
            prompts=prompts,
            root=temp_project_with_migrations,
        )
        assert "result" in resp, tool_name
        assert resp["result"]["isError"] is False, tool_name


def test_mcp_server_resources_read(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    import mcp_server
    tools = mcp_server.build_mcp_tools()
    resources = mcp_server.build_mcp_resources()
    prompts = mcp_server.build_mcp_prompts()
    dispatcher = mcp_server._make_dispatcher(temp_project_with_migrations)

    req = {
        "jsonrpc": "2.0", "id": 4, "method": "resources/read",
        "params": {"uri": "we-together://schema/version"},
    }
    resp = mcp_server.handle_request(
        req, dispatcher=dispatcher, tools=tools,
        resources=resources, prompts=prompts, root=temp_project_with_migrations,
    )
    assert resp["result"]["contents"][0]["text"] == "1"


def test_mcp_server_prompts_get(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    import mcp_server
    tools = mcp_server.build_mcp_tools()
    resources = mcp_server.build_mcp_resources()
    prompts = mcp_server.build_mcp_prompts()
    dispatcher = mcp_server._make_dispatcher(temp_project_with_migrations)

    req = {
        "jsonrpc": "2.0", "id": 5, "method": "prompts/get",
        "params": {"name": "we_together_scene_reply",
                   "arguments": {"scene_id": "s1", "user_input": "hi"}},
    }
    resp = mcp_server.handle_request(
        req, dispatcher=dispatcher, tools=tools,
        resources=resources, prompts=prompts, root=temp_project_with_migrations,
    )
    msgs = resp["result"]["messages"]
    assert msgs[0]["role"] == "assistant"
    assert msgs[0]["content"]["type"] == "text"
    assert "scene s1" in msgs[0]["content"]["text"]
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == {"type": "text", "text": "hi"}


def test_mcp_server_main_accepts_tenant_id(tmp_path, monkeypatch):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.tenant_router import resolve_tenant_root

    tenant_root = resolve_tenant_root(tmp_path, "alpha")
    bootstrap_project(tenant_root)
    import mcp_server

    monkeypatch.setattr(
        "sys.argv",
        ["mcp_server.py", "--root", str(tmp_path), "--tenant-id", "alpha"],
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert mcp_server.main() == 0


def test_mcp_server_main_supports_content_length_framing(tmp_path, monkeypatch):
    import mcp_server

    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    framed = f"Content-Length: {len(body)}\r\n\r\n{body}"
    stdin = io.StringIO(framed)
    stdout = io.StringIO()

    monkeypatch.setattr("sys.argv", ["mcp_server.py", "--root", str(tmp_path)])
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("sys.stdout", stdout)

    assert mcp_server.main() == 0

    output = stdout.getvalue()
    assert "Content-Length:" in output
    assert '"serverInfo": {"name": "we-together"' in output


def test_mcp_server_main_ignores_initialized_notification(tmp_path, monkeypatch):
    import mcp_server

    init_body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    notif_body = json.dumps(
        {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    )
    framed = (
        f"Content-Length: {len(init_body)}\r\n\r\n{init_body}"
        f"Content-Length: {len(notif_body)}\r\n\r\n{notif_body}"
    )
    stdin = io.StringIO(framed)
    stdout = io.StringIO()

    monkeypatch.setattr("sys.argv", ["mcp_server.py", "--root", str(tmp_path)])
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("sys.stdout", stdout)

    assert mcp_server.main() == 0

    output = stdout.getvalue()
    assert output.count("Content-Length:") == 1
    assert "notifications/initialized" not in output


def test_mcp_server_main_handles_framed_unicode_tool_call(
    temp_project_with_migrations, monkeypatch,
):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    import mcp_server

    tool_body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "we_together_graph_summary",
                "arguments": {"scene_id": "你好"},
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")
    resource_body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "resources/read",
            "params": {"uri": "we-together://schema/version"},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    framed = (
        b"Content-Length: " + str(len(tool_body)).encode("ascii") + b"\r\n\r\n" + tool_body
        + b"Content-Length: " + str(len(resource_body)).encode("ascii") + b"\r\n\r\n" + resource_body
    )
    stdin_bytes = io.BytesIO(framed)
    stdin = io.TextIOWrapper(stdin_bytes, encoding="utf-8")
    stdout_bytes = io.BytesIO()
    stdout = io.TextIOWrapper(stdout_bytes, encoding="utf-8")

    monkeypatch.setattr("sys.argv", ["mcp_server.py", "--root", str(temp_project_with_migrations)])
    monkeypatch.setattr("sys.stdin", stdin)
    monkeypatch.setattr("sys.stdout", stdout)

    assert mcp_server.main() == 0

    stdout.flush()
    output = stdout_bytes.getvalue().decode("utf-8")
    assert output.count("Content-Length:") == 2
    assert '"id": 1' in output
    assert '"id": 2' in output


def test_adapters_equivalent_payload_structure():
    """Claude + OpenAI 两个 adapter 接相同 SkillRequest 产的 payload 都包含 system + messages"""
    from we_together.runtime.adapters.claude_adapter import ClaudeSkillAdapter
    from we_together.runtime.adapters.openai_adapter import OpenAISkillAdapter
    from we_together.runtime.skill_runtime import SkillRequest

    req = SkillRequest(
        system_prompt="sys", messages=[{"role": "user", "content": "hi"}],
        retrieval_package={}, scene_id="s1", user_input="hi",
    )
    ca = ClaudeSkillAdapter().build_payload(req)
    oa = OpenAISkillAdapter().build_payload(req)
    # Claude 保持 system 独立字段
    assert ca["system"] == "sys"
    assert ca["messages"][0]["content"] == "hi"
    # OpenAI 把 system 拼进 messages
    assert oa["messages"][0]["role"] == "system"
    assert oa["messages"][1]["content"] == "hi"


def test_package_skill_pack_unpack_roundtrip(tmp_path):
    from we_together.packaging.skill_packager import pack_skill, unpack_skill

    # 构造最小 skill 目录
    src = tmp_path / "src"
    src.mkdir()
    (src / "SKILL.md").write_text("# test", encoding="utf-8")
    (src / "db").mkdir()
    (src / "db" / "migrations").mkdir()
    (src / "db" / "migrations" / "0001.sql").write_text("SELECT 1;", encoding="utf-8")

    pkg = tmp_path / "test.weskill.zip"
    r = pack_skill(src, pkg, skill_version="0.14.0", schema_version="0015")
    assert r["file_count"] >= 1
    assert pkg.exists()

    target = tmp_path / "unpacked"
    r2 = unpack_skill(pkg, target)
    assert r2["manifest"]["skill_version"] == "0.14.0"
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# test"


def test_package_skill_cli_pack_infers_version_and_schema_defaults(tmp_path, monkeypatch):
    import package_skill

    src = tmp_path / "src"
    (src / "db" / "migrations").mkdir(parents=True)
    (src / "src" / "we_together").mkdir(parents=True)
    (src / "SKILL.md").write_text("# test", encoding="utf-8")
    (src / "db" / "migrations" / "0001.sql").write_text("SELECT 1;", encoding="utf-8")
    (src / "db" / "migrations" / "0015.sql").write_text("SELECT 15;", encoding="utf-8")
    (src / "pyproject.toml").write_text(
        "[project]\nname = 'fake-skill'\nversion = '9.9.9'\n",
        encoding="utf-8",
    )
    (src / "src" / "we_together" / "cli.py").write_text(
        'VERSION = "9.9.9"\n',
        encoding="utf-8",
    )
    (src / "src" / "we_together" / "__init__.py").write_text(
        '__version__ = "9.9.9"\n',
        encoding="utf-8",
    )

    pkg = tmp_path / "auto.weskill.zip"
    monkeypatch.setattr(
        "sys.argv",
        ["package_skill.py", "pack", "--root", str(src), "--output", str(pkg)],
    )

    package_skill.main()

    with zipfile.ZipFile(pkg, "r") as zf:
        manifest = json.loads(zf.read("manifest.json"))

    assert manifest["skill_version"] == "9.9.9"
    assert manifest["schema_version"] == "0015"
