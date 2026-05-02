from we_together.runtime.adapters.claude_adapter import ClaudeSkillAdapter
from we_together.runtime.adapters.openai_adapter import OpenAISkillAdapter
from we_together.runtime.skill_runtime import SkillRequest

TOOL = {
    "name": "graph_summary",
    "description": "返回当前图谱快照摘要",
    "input_schema": {
        "type": "object",
        "properties": {"scope": {"type": "string"}},
        "required": [],
    },
}


def _make_request():
    return SkillRequest(
        system_prompt="sys",
        messages=[{"role": "user", "content": "hi"}],
        retrieval_package={},
        scene_id="scene_x",
        user_input="hi",
        tools=[TOOL],
    )


def test_claude_adapter_translates_tools():
    payload = ClaudeSkillAdapter().build_payload(_make_request())
    assert "tools" in payload
    assert payload["tools"][0]["name"] == "graph_summary"
    assert "input_schema" in payload["tools"][0]


def test_openai_adapter_translates_tools():
    payload = OpenAISkillAdapter().build_payload(_make_request())
    assert "tools" in payload
    t = payload["tools"][0]
    assert t["type"] == "function"
    assert t["function"]["name"] == "graph_summary"
    assert "parameters" in t["function"]


def test_adapters_omit_tools_when_empty():
    req = SkillRequest(
        system_prompt="s", messages=[], retrieval_package={}, scene_id="x",
        user_input="", tools=[],
    )
    p1 = ClaudeSkillAdapter().build_payload(req)
    p2 = OpenAISkillAdapter().build_payload(req)
    assert "tools" not in p1
    assert "tools" not in p2


def test_skill_request_roundtrip_with_tools():
    req = _make_request()
    d = req.to_dict()
    assert d["tools"][0]["name"] == "graph_summary"
