from we_together.llm.providers.mock import MockLLMClient
from we_together.runtime.adapters import ClaudeSkillAdapter, OpenAISkillAdapter
from we_together.runtime.prompt_composer import build_skill_request


def _pkg():
    return {
        "scene_summary": {"scene_id": "scene_t", "scene_type": "private_chat", "summary": "t"},
        "environment_constraints": {},
        "participants": [
            {
                "person_id": "p1", "display_name": "A",
                "scene_role": "participant", "speak_eligibility": "allowed",
            }
        ],
        "active_relations": [],
        "relevant_memories": [],
        "current_states": [],
        "activation_map": [],
        "response_policy": {
            "mode": "single_primary",
            "primary_speaker": "p1",
            "supporting_speakers": ["p2"],
            "silenced_participants": [],
        },
        "safety_and_budget": {},
        "recent_changes": [],
    }


def test_claude_adapter_build_payload_has_system_and_messages():
    req = build_skill_request(retrieval_package=_pkg(), user_input="hi")
    adapter = ClaudeSkillAdapter()
    payload = adapter.build_payload(req)
    assert "system" in payload
    assert isinstance(payload["messages"], list)
    assert payload["messages"][-1]["content"] == "hi"
    assert payload["metadata"]["scene_id"] == "scene_t"


def test_openai_adapter_build_payload_prepends_system():
    req = build_skill_request(retrieval_package=_pkg(), user_input="hi")
    adapter = OpenAISkillAdapter()
    payload = adapter.build_payload(req)
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][-1] == {"role": "user", "content": "hi"}


def test_both_adapters_semantically_equivalent():
    req = build_skill_request(retrieval_package=_pkg(), user_input="hi")
    a = ClaudeSkillAdapter().build_payload(req)
    b = OpenAISkillAdapter().build_payload(req)
    # 拼接后两套 messages 的 user/assistant 序列一致
    a_non_system = a["messages"]
    b_non_system = [m for m in b["messages"] if m["role"] != "system"]
    assert a_non_system == b_non_system
    # system 内容一致
    assert a["system"] == b["messages"][0]["content"]


def test_claude_adapter_invoke_with_mock_llm():
    req = build_skill_request(retrieval_package=_pkg(), user_input="hi")
    mock = MockLLMClient(scripted_responses=["你好"])
    resp = ClaudeSkillAdapter().invoke(req, llm_client=mock)
    assert resp.text == "你好"
    assert resp.speaker_person_id == "p1"
    assert resp.supporting_speakers == ["p2"]
    assert resp.raw["adapter"] == "claude"


def test_openai_adapter_invoke_with_mock_llm():
    req = build_skill_request(retrieval_package=_pkg(), user_input="hi")
    mock = MockLLMClient(scripted_responses=["hello"])
    resp = OpenAISkillAdapter().invoke(req, llm_client=mock)
    assert resp.text == "hello"
    assert resp.raw["adapter"] == "openai_compat"
