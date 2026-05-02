import hashlib
import hmac
import json

from we_together.runtime.adapters.coze_adapter import (
    build_plugin_schema,
    parse_plugin_invocation,
)
from we_together.runtime.adapters.feishu_adapter import (
    FeishuSkillAdapter,
    format_reply,
    parse_webhook_payload,
    verify_signature,
)
from we_together.runtime.adapters.langchain_adapter import (
    WeTogetherLCTool,
    invoke_as_lc_tool,
)
from we_together.runtime.adapters.mcp_adapter import build_mcp_tools
from we_together.runtime.skill_runtime import SkillResponse


# --- Feishu ---

def test_feishu_parse_text_message():
    raw = {
        "event_id": "e1",
        "event_type": "im.message.receive_v1",
        "message": {"content": json.dumps({"text": "你好"}), "msg_type": "text"},
        "sender": {"user_id": "u1", "name": "Alice"},
    }
    req = parse_webhook_payload(raw, scene_id="s_work")
    assert req.user_input == "你好"
    assert req.metadata["sender_user_id"] == "u1"
    assert req.metadata["adapter"] == "feishu"


def test_feishu_format_reply():
    resp = SkillResponse(text="收到")
    msg = format_reply(resp, chat_id="c1")
    assert msg["msg_type"] == "text"
    assert msg["content"]["text"] == "收到"
    assert msg["chat_id"] == "c1"


def test_feishu_verify_signature_valid():
    secret = "sec"
    ts, nonce, body = "1000", "n", b"{}"
    mac = hmac.new(secret.encode(), (ts + nonce).encode() + body,
                    hashlib.sha256).hexdigest()
    assert verify_signature(secret=secret, timestamp=ts, nonce=nonce, body=body,
                             signature=mac)


def test_feishu_verify_signature_invalid():
    assert not verify_signature(secret="x", timestamp="1", nonce="2", body=b"",
                                  signature="bad")


def test_feishu_adapter_class_roundtrip():
    a = FeishuSkillAdapter()
    req = a.parse({"message": {"content": "hi"}}, scene_id="s")
    assert req.user_input == "hi"


# --- LangChain ---

def test_lc_tool_invokes_run_turn():
    calls = []
    def _run_turn(scene_id, text):
        calls.append((scene_id, text))
        return f"ok:{text}"
    tool = WeTogetherLCTool(_run_turn)
    out = tool.run({"scene_id": "s1", "input": "hi"})
    assert out == "ok:hi"
    assert calls == [("s1", "hi")]


def test_lc_tool_requires_scene_id():
    import pytest
    with pytest.raises(ValueError):
        invoke_as_lc_tool({"input": "x"}, run_turn_fn=lambda s, t: "")


# --- Coze ---

def test_coze_plugin_schema_shape():
    sch = build_plugin_schema()
    assert sch["plugin_name"] == "we_together"
    assert any(a["name"] == "run_turn" for a in sch["actions"])


def test_coze_parse_invocation():
    req = parse_plugin_invocation({
        "action": "run_turn",
        "parameters": {"scene_id": "s", "input": "hi"},
    })
    assert req.scene_id == "s"
    assert req.user_input == "hi"


# --- MCP ---

def test_mcp_tools_have_input_schema():
    tools = build_mcp_tools()
    assert all("inputSchema" in t and "name" in t for t in tools)
    names = {t["name"] for t in tools}
    assert "we_together_run_turn" in names


def test_mcp_tools_extra_merge():
    tools = build_mcp_tools(extra=[{"name": "custom", "description": "",
                                     "inputSchema": {"type": "object"}}])
    assert any(t["name"] == "custom" for t in tools)
