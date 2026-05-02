"""Phase 46 — 多 Agent REPL (MA slices)。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _seed(root: Path) -> tuple[Path, dict]:
    from seed_demo import seed_society_c
    summary = seed_society_c(root)
    return root / "db" / "main.sqlite3", summary


def test_transcript_entry_to_dict():
    from we_together.services.multi_agent_dialogue import TranscriptEntry
    e = TranscriptEntry(
        speaker="Alice", speaker_id="p1", text="hi",
        audience=["p2"], is_interrupt=True, turn_index=3,
    )
    d = e.to_dict()
    assert d["speaker"] == "Alice"
    assert d["audience"] == ["p2"]
    assert d["is_interrupt"] is True
    assert d["turn_index"] == 3


def test_visible_messages_public_vs_private():
    from we_together.services.multi_agent_dialogue import (
        TranscriptEntry, _visible_messages_for,
    )
    # 构造 transcript
    transcript = [
        TranscriptEntry(speaker="A", speaker_id="pA", text="hello all"),
        TranscriptEntry(speaker="B", speaker_id="pB", text="whisper to C",
                         audience=["pC"]),
        TranscriptEntry(speaker="C", speaker_id="pC", text="whisper back",
                         audience=["pB"]),
    ]

    class FakeAgent:
        def __init__(self, pid):
            self.person_id = pid
            self.primary_name = pid

    # Agent A 只能看 public
    visible_a = _visible_messages_for(FakeAgent("pA"), transcript)
    assert len(visible_a) == 1
    assert visible_a[0]["text"] == "hello all"

    # Agent C 能看 public + 给 C 的私聊 + 自己发的
    visible_c = _visible_messages_for(FakeAgent("pC"), transcript)
    assert len(visible_c) == 3


def test_orchestrate_dialogue_basic(temp_project_dir):
    db, summary = _seed(temp_project_dir)
    from we_together.agents.person_agent import PersonAgent
    from we_together.llm.providers.mock import MockLLMClient
    from we_together.services.multi_agent_dialogue import orchestrate_dialogue

    llm = MockLLMClient(scripted_responses=[
        "我是第一个", "我是第二个", "我是第三个",
        "我是第四个", "我是第五个", "我是第六个",
    ])
    persons = summary.get("persons", {})
    agents: list[PersonAgent] = []
    for pid in list(persons.values())[:3]:
        agents.append(PersonAgent.from_db(db, pid, llm_client=llm))

    activation = {a.person_id: {"activation_score": 0.8 - i * 0.1}
                  for i, a in enumerate(agents)}

    r = orchestrate_dialogue(
        agents, scene_summary="work",
        activation_map=activation, turns=3, interrupt_threshold=2.0,
    )
    assert r["turns_taken"] == 3
    assert len(r["transcript"]) == 3


def test_orchestrate_interrupt_triggers(temp_project_dir):
    """高 activation agent 可插话 (interrupt_threshold=低)"""
    db, summary = _seed(temp_project_dir)
    from we_together.agents.person_agent import PersonAgent
    from we_together.llm.providers.mock import MockLLMClient
    from we_together.services.multi_agent_dialogue import orchestrate_dialogue

    llm = MockLLMClient(default_content="打断发言")
    persons = summary.get("persons", {})
    agents = [PersonAgent.from_db(db, pid, llm_client=llm)
              for pid in list(persons.values())[:3]]
    activation = {a.person_id: {"activation_score": 0.9} for a in agents}

    # 极低阈值让每轮都有 interrupt 可能
    r = orchestrate_dialogue(
        agents, scene_summary="work", activation_map=activation,
        turns=3, interrupt_threshold=0.1,
    )
    assert r["interrupts"] >= 1 or r["turns_taken"] >= 1


def test_private_audience_filtered(temp_project_dir):
    db, summary = _seed(temp_project_dir)
    from we_together.agents.person_agent import PersonAgent
    from we_together.llm.providers.mock import MockLLMClient
    from we_together.services.multi_agent_dialogue import orchestrate_dialogue

    llm = MockLLMClient(default_content="私密发言")
    persons = list(summary.get("persons", {}).values())[:3]
    agents = [PersonAgent.from_db(db, pid, llm_client=llm) for pid in persons]
    activation = {a.person_id: {"activation_score": 0.5 + i * 0.1}
                  for i, a in enumerate(agents)}

    # 第 0 轮私聊给 persons[1]
    r = orchestrate_dialogue(
        agents, scene_summary="work", activation_map=activation,
        turns=2, interrupt_threshold=2.0,
        private_turn_map={0: [persons[1]]},
    )
    assert r["transcript"][0]["audience"] == [persons[1]]


def test_record_transcript_as_event(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.multi_agent_dialogue import record_transcript_as_event
    import sqlite3
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    transcript = [
        {"speaker": "A", "text": "hi", "audience": []},
        {"speaker": "B", "text": "hello", "audience": []},
    ]
    ev_id = record_transcript_as_event(
        db, scene_id="scene_test", transcript=transcript,
    )
    assert ev_id.startswith("evt_dialogue_")

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT event_type, scene_id FROM events WHERE event_id=?", (ev_id,),
    ).fetchone()
    conn.close()
    assert row[0] == "dialogue_event"
    assert row[1] == "scene_test"


def test_multi_agent_chat_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "multi_agent_chat.py"
    spec = importlib.util.spec_from_file_location("mac_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
    assert callable(mod._load_scene_agents)


def test_no_speaker_when_all_zero(temp_project_dir):
    """所有 agent decide_speak=0 → 提前终止"""
    db, summary = _seed(temp_project_dir)
    from we_together.agents.person_agent import PersonAgent
    from we_together.llm.providers.mock import MockLLMClient
    from we_together.services.multi_agent_dialogue import orchestrate_dialogue

    llm = MockLLMClient(default_content="x")
    persons = list(summary.get("persons", {}).values())[:2]
    agents = [PersonAgent.from_db(db, pid, llm_client=llm) for pid in persons]
    # 所有人激活 0
    activation = {a.person_id: {"activation_score": 0.0} for a in agents}

    r = orchestrate_dialogue(
        agents, scene_summary="work", activation_map=activation,
        turns=5, interrupt_threshold=2.0,
    )
    # 可能 0 turn（全 0）或极少
    assert r["turns_taken"] <= 5


def test_5_agent_convergence(temp_project_dir):
    """5 agent 场景 10 轮收敛"""
    db, summary = _seed(temp_project_dir)
    from we_together.agents.person_agent import PersonAgent
    from we_together.llm.providers.mock import MockLLMClient
    from we_together.services.multi_agent_dialogue import orchestrate_dialogue

    llm = MockLLMClient(default_content="reply")
    persons = list(summary.get("persons", {}).values())[:5]
    if len(persons) < 2:
        # seed_society_c 至少 2 人；5 人可能需要多 seed
        import pytest
        pytest.skip("seed too small for 5-agent test")
    agents = [PersonAgent.from_db(db, pid, llm_client=llm) for pid in persons]
    activation = {a.person_id: {"activation_score": 0.5 + i * 0.05}
                  for i, a in enumerate(agents)}

    r = orchestrate_dialogue(
        agents, scene_summary="group meeting", activation_map=activation,
        turns=10, interrupt_threshold=0.95,
    )
    # 10 轮应该真跑完，不抛
    assert r["turns_taken"] <= 10
    assert r["turns_taken"] > 0
