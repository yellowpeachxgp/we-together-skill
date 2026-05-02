import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.runtime.agent_runner import run_tool_use_loop  # noqa: E402
from we_together.runtime.skill_runtime import SkillRequest  # noqa: E402
from we_together.runtime.streaming import (  # noqa: E402
    StreamingSkillResponse,
    mock_stream_chunks,
)
from we_together.services.chat_service import run_turn  # noqa: E402


def _req() -> SkillRequest:
    return SkillRequest(
        system_prompt="你是测试代理。",
        messages=[{"role": "user", "content": "查询图谱并回答"}],
        retrieval_package={"response_policy": {"primary_speaker": "p_alice"}},
        scene_id="s_test",
        user_input="查询图谱并回答",
        tools=[{"name": "graph_summary", "description": "g"}],
    )


# --- agent_runner ---

def test_agent_runner_tool_then_respond(tmp_path, temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    llm = MockLLMClient(scripted_json=[
        {"action": "tool_call", "tool": "graph_summary", "args": {}},
        {"action": "respond", "text": "图谱健康"},
    ])
    dispatcher = {"graph_summary": lambda args: "ok"}
    result = run_tool_use_loop(
        _req(), llm_client=llm, tool_dispatcher=dispatcher,
        db_path=db, max_iters=3,
    )
    assert result.response.text == "图谱健康"
    assert [s["type"] for s in result.steps] == ["tool_call", "tool_result", "respond"]
    assert len(result.event_ids) == 2
    assert result.response.raw.get("tool_use") is True


def test_agent_runner_tool_error_path(tmp_path, temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    def _boom(args):
        raise RuntimeError("tool exploded")
    llm = MockLLMClient(scripted_json=[
        {"action": "tool_call", "tool": "bomb", "args": {}},
        {"action": "respond", "text": "已处理错误"},
    ])
    result = run_tool_use_loop(
        _req(), llm_client=llm,
        tool_dispatcher={"bomb": _boom},
        db_path=db,
    )
    tr = next(s for s in result.steps if s["type"] == "tool_result")
    assert tr["is_error"] is True
    assert "tool exploded" in tr["result"]
    assert result.response.text == "已处理错误"


def test_agent_runner_max_iters_exhausted(tmp_path):
    llm = MockLLMClient(default_json={
        "action": "tool_call", "tool": "echo", "args": {},
    })
    result = run_tool_use_loop(
        _req(), llm_client=llm,
        tool_dispatcher={"echo": lambda a: "x"}, db_path=None, max_iters=2,
    )
    assert "exhausted" in result.response.text


# --- streaming ---

def test_streaming_response_roundtrip():
    chunks = list(mock_stream_chunks("你好世界", chunk_size=2))
    assert "".join(chunks) == "你好世界"

    stream = StreamingSkillResponse(chunks=mock_stream_chunks("hello, we-together"))
    collected: list = []
    for c in stream:
        collected.append(c)
    final = stream.finalize()
    assert final.text == "hello, we-together"
    assert "".join(collected) == "hello, we-together"


def test_streaming_finalize_auto_drain():
    stream = StreamingSkillResponse(chunks=mock_stream_chunks("abcdef", chunk_size=2))
    final = stream.finalize()
    assert final.text == "abcdef"


# --- chat_service run_turn 带 tools ---

def test_run_turn_with_tools_full_flow(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    llm = MockLLMClient(scripted_json=[
        {"action": "tool_call", "tool": "graph_summary", "args": {}},
        {"action": "respond", "text": "我查了图谱，一切正常。"},
    ])
    result = run_turn(
        db_path=db, scene_id=scene_id, user_input="汇报图谱",
        llm_client=llm,
        adapter_name="openai_compat",
        tools=[{"name": "graph_summary", "description": "总览"}],
        tool_dispatcher={"graph_summary": lambda a: "persons=8,relations=8"},
    )
    assert result["response"]["text"] == "我查了图谱，一切正常。"
    assert len(result["agent_steps"]) >= 3
    assert len(result["agent_event_ids"]) == 2
