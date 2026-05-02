from we_together.runtime.prompt_composer import (
    build_skill_request,
    compose_system_prompt,
    compose_messages,
)
from we_together.runtime.skill_runtime import SkillRequest, SkillResponse


def _sample_package():
    return {
        "scene_summary": {
            "scene_id": "scene_x",
            "scene_type": "private_chat",
            "summary": "晚间聊天",
            "group_id": None,
        },
        "environment_constraints": {
            "location_scope": "remote",
            "channel_scope": "private_dm",
            "visibility_scope": "mutual_visible",
            "activation_barrier": None,
        },
        "participants": [
            {
                "person_id": "person_alice",
                "display_name": "Alice",
                "scene_role": "participant",
                "speak_eligibility": "allowed",
                "persona_summary": "温柔理性",
                "style_summary": "说话简短",
                "boundary_summary": None,
            }
        ],
        "active_relations": [
            {
                "relation_id": "rel_1",
                "participants": [
                    {"person_id": "person_alice", "display_name": "Alice"},
                    {"person_id": "person_bob", "display_name": "Bob"},
                ],
                "core_type": "friendship",
                "custom_label": "朋友",
                "strength": 0.7,
                "short_summary": "多年朋友",
            }
        ],
        "relevant_memories": [
            {
                "memory_id": "mem_1",
                "memory_type": "shared_memory",
                "summary": "一起熬夜写方案",
                "relevance_score": 0.9,
                "confidence": 0.8,
            }
        ],
        "current_states": [
            {
                "state_id": "st_1",
                "scope_type": "scene",
                "scope_id": "scene_x",
                "state_type": "mood",
                "value": {"mood": "calm"},
                "confidence": 0.7,
                "is_inferred": True,
            }
        ],
        "activation_map": [
            {
                "person_id": "person_alice",
                "activation_score": 0.95,
                "activation_state": "explicit",
                "activation_reason_summary": "scene participant",
            }
        ],
        "response_policy": {
            "mode": "single_primary",
            "primary_speaker": "person_alice",
            "supporting_speakers": [],
            "silenced_participants": [],
        },
        "safety_and_budget": {},
        "recent_changes": [
            {
                "patch_id": "p1",
                "operation": "update_state",
                "target_type": "state",
                "reason": "dialogue mood",
                "applied_at": "2026-04-12T00:00:00+00:00",
            }
        ],
    }


def test_compose_system_prompt_contains_sections():
    prompt = compose_system_prompt(_sample_package())
    assert "## 场景" in prompt
    assert "scene_x" in prompt
    assert "## 参与者" in prompt
    assert "Alice" in prompt
    assert "## 活跃关系" in prompt
    assert "## 相关记忆" in prompt
    assert "一起熬夜写方案" in prompt
    assert "## 当前状态" in prompt
    assert "## 回应策略" in prompt
    assert "single_primary" in prompt
    assert "## 最近图谱变化" in prompt


def test_compose_messages_wraps_user_input():
    msgs = compose_messages("你好")
    assert msgs == [{"role": "user", "content": "你好"}]


def test_compose_messages_preserves_history():
    history = [{"role": "assistant", "content": "上一轮回应"}]
    msgs = compose_messages("继续", history=history)
    assert len(msgs) == 2
    assert msgs[0]["role"] == "assistant"
    assert msgs[-1]["content"] == "继续"


def test_build_skill_request_returns_structured_object():
    pkg = _sample_package()
    req = build_skill_request(retrieval_package=pkg, user_input="在吗")
    assert isinstance(req, SkillRequest)
    assert req.scene_id == "scene_x"
    assert "## 参与者" in req.system_prompt
    assert req.messages[-1] == {"role": "user", "content": "在吗"}


def test_skill_request_to_dict_is_serializable():
    pkg = _sample_package()
    req = build_skill_request(retrieval_package=pkg, user_input="hi")
    d = req.to_dict()
    assert set(d.keys()) == {
        "schema_version",
        "system_prompt", "messages", "retrieval_package", "scene_id", "user_input",
        "metadata", "tools",
    }
    assert d["schema_version"] == "1"


def test_skill_response_to_dict():
    r = SkillResponse(text="好的", speaker_person_id="person_alice")
    d = r.to_dict()
    assert d["text"] == "好的"
    assert d["speaker_person_id"] == "person_alice"
