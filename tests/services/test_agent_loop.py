import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.services.agent_loop_service import run_turn_agent  # noqa: E402


def test_agent_loop_tool_call_then_respond(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    # Mock：先 tool_call（graph_summary）再 respond
    llm = MockLLMClient(scripted_json=[
        {"action": "tool_call", "tool": "graph_summary", "args": {"scope": "scene"}},
        {"action": "respond", "text": "已汇总当前图谱"},
    ])

    dispatcher = {"graph_summary": lambda args: f"summary scope={args.get('scope')}"}

    result = run_turn_agent(
        db_path=db_path, scene_id=scene_id, user_input="help",
        tool_dispatcher=dispatcher, llm_client=llm, max_iters=3,
    )

    assert result.final_text == "已汇总当前图谱"
    step_types = [s.step_type for s in result.steps]
    assert step_types == ["tool_call", "tool_result", "respond"]
    # 事件应写入 events 表
    c = sqlite3.connect(db_path)
    count = c.execute(
        "SELECT COUNT(*) FROM events WHERE event_type IN ('tool_use_event','tool_result_event','dialogue_event') "
        "AND source_type = 'agent_loop'"
    ).fetchone()[0]
    c.close()
    assert count == 3


def test_agent_loop_unknown_tool_gracefully(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    llm = MockLLMClient(scripted_json=[
        {"action": "tool_call", "tool": "nonexistent", "args": {}},
        {"action": "respond", "text": "done anyway"},
    ])
    result = run_turn_agent(
        db_path=db_path, scene_id=scene_id, user_input="x",
        tool_dispatcher={}, llm_client=llm,
    )
    assert result.final_text == "done anyway"
    tool_steps = [s for s in result.steps if s.step_type == "tool_result"]
    assert "[unknown tool" in tool_steps[0].result


def test_agent_loop_max_iters_safety(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    # 永不 respond 的 LLM：不断 tool_call
    llm = MockLLMClient(default_json={
        "action": "tool_call", "tool": "echo", "args": {}
    })
    result = run_turn_agent(
        db_path=db_path, scene_id=scene_id, user_input="x",
        tool_dispatcher={"echo": lambda _: "echoed"},
        llm_client=llm, max_iters=2,
    )
    assert "exhausted" in result.final_text
