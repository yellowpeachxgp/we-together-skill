import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.observability.llm_hooks import (  # noqa: E402
    LangSmithStubSink,
    clear_hooks,
    register_hook,
    timed_call,
)
from we_together.runtime.agent_runner import run_tool_use_loop  # noqa: E402
from we_together.runtime.skill_runtime import SkillRequest  # noqa: E402
from we_together.services.chat_service import run_turn, run_turn_stream  # noqa: E402


def _req(tools: list[dict]) -> SkillRequest:
    return SkillRequest(
        system_prompt="你是测试代理。",
        messages=[{"role": "user", "content": "用 tool 查询"}],
        retrieval_package={"response_policy": {"primary_speaker": "p_x"}},
        scene_id="s_test",
        user_input="用 tool 查询",
        tools=tools,
    )


# --- TL-1/2/3: chat_with_tools native 路径 ---

def test_mock_chat_with_tools_returns_tool_uses():
    llm = MockLLMClient(scripted_tool_uses=[
        {"text": "", "tool_uses": [{"id": "tu1", "name": "graph_summary",
                                      "input": {"scope": "scene"}}],
         "stop_reason": "tool_use"},
        {"text": "图谱正常", "tool_uses": [], "stop_reason": "end_turn"},
    ])
    tools = [{"name": "graph_summary", "description": "g",
              "input_schema": {"type": "object"}}]
    result = run_tool_use_loop(
        _req(tools), llm_client=llm,
        tool_dispatcher={"graph_summary": lambda a: "ok"},
        db_path=None, max_iters=3,
    )
    assert result.response.text == "图谱正常"
    # native 路径：raw 有 "native": True
    assert result.response.raw.get("native") is True
    # 至少一次 tool_call + tool_result + respond
    types = [s["type"] for s in result.steps]
    assert "tool_call" in types and "tool_result" in types and "respond" in types


def test_mock_chat_with_tools_multiple_tool_uses_per_turn():
    """同一次 response 里有多个 tool_use，应顺序处理。"""
    llm = MockLLMClient(scripted_tool_uses=[
        {"text": "", "tool_uses": [
            {"id": "tu1", "name": "get_time", "input": {}},
            {"id": "tu2", "name": "get_weather", "input": {"city": "SF"}},
        ], "stop_reason": "tool_use"},
        {"text": "综合结果", "tool_uses": [], "stop_reason": "end_turn"},
    ])
    tools = [
        {"name": "get_time", "description": "time"},
        {"name": "get_weather", "description": "weather"},
    ]
    result = run_tool_use_loop(
        _req(tools), llm_client=llm,
        tool_dispatcher={
            "get_time": lambda a: "12:00",
            "get_weather": lambda a: "sunny",
        },
        db_path=None,
    )
    tool_calls = [s for s in result.steps if s["type"] == "tool_call"]
    assert len(tool_calls) == 2
    assert {tc["tool"] for tc in tool_calls} == {"get_time", "get_weather"}


def test_fallback_chat_json_still_works():
    """没有 chat_with_tools 的旧 mock 仍走 chat_json action 协议。"""
    class OldMock:
        provider = "mock"
        def chat_json(self, messages, schema_hint, **kw):
            return {"action": "respond", "text": "旧协议"}
    result = run_tool_use_loop(
        _req([{"name": "t"}]), llm_client=OldMock(),
        tool_dispatcher={}, db_path=None,
    )
    assert result.response.text == "旧协议"


# --- TL-4: streaming ---

def test_mock_chat_stream_yields_chunks():
    llm = MockLLMClient(scripted_stream=[["hel", "lo ", "wor", "ld"]])
    chunks = list(llm.chat_stream([]))
    assert chunks == ["hel", "lo ", "wor", "ld"]


def test_run_turn_stream_full_flow(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    llm = MockLLMClient(scripted_stream=[["你", "们", "好"]])
    stream = run_turn_stream(
        db_path=db, scene_id=scene_id, user_input="hi",
        llm_client=llm,
    )
    collected = list(stream)
    assert collected == ["你", "们", "好"]
    result = stream.finalize_turn()
    assert result["response"]["text"] == "你们好"
    assert result["streaming"] is True
    assert result["event_id"]


# --- TL-6: observability hooks ---

def test_llm_hook_captures_event():
    clear_hooks()
    sink = LangSmithStubSink()
    register_hook(sink)
    with timed_call(provider="anthropic", method="chat",
                     extra={"tokens": 42}):
        pass
    assert len(sink.events) == 1
    evt = sink.events[0]
    assert evt["provider"] == "anthropic"
    assert evt["method"] == "chat"
    assert evt["tokens"] == 42
    assert "duration_ms" in evt
    clear_hooks()


def test_llm_hook_captures_error():
    clear_hooks()
    sink = LangSmithStubSink()
    register_hook(sink)
    try:
        with timed_call(provider="openai_compat", method="chat"):
            raise ValueError("boom")
    except ValueError:
        pass
    assert sink.events[0]["error"] is True
    assert "boom" in sink.events[0]["error_msg"]
    clear_hooks()
