from we_together.services.patch_service import (
    build_patch,
    infer_narration_patches,
    infer_text_chat_patches,
    infer_email_patches,
)


def test_build_patch_creates_structured_payload():
    patch = build_patch(
        source_event_id="evt_1",
        target_type="state",
        target_id="state_1",
        operation="update_state",
        payload={"value": {"mood": "tense"}},
        confidence=0.9,
        reason="recent conflict event",
    )

    assert patch["source_event_id"] == "evt_1"
    assert patch["operation"] == "update_state"
    assert patch["payload_json"]["value"]["mood"] == "tense"


def test_infer_narration_patches_creates_memory_and_relation_links():
    patches = infer_narration_patches(
        source_event_id="evt_1",
        text="小王和小李以前是同事，现在还是朋友。",
        person_ids=["person_1", "person_2"],
        relation_ids=["relation_work", "relation_friend"],
    )

    operations = [patch["operation"] for patch in patches]
    link_patches = [patch for patch in patches if patch["operation"] == "link_entities"]
    memory_patches = [patch for patch in patches if patch["operation"] == "create_memory"]
    state_patches = [patch for patch in patches if patch["operation"] == "update_state"]

    assert operations.count("create_memory") == 1
    assert operations.count("link_entities") == 2
    assert operations.count("update_state") >= 1
    assert memory_patches[0]["target_type"] == "memory"
    assert memory_patches[0]["payload_json"]["memory_type"] == "shared_memory"
    assert link_patches[0]["payload_json"]["from_type"] == "relation"
    assert state_patches[0]["payload_json"]["scope_type"] == "relation"


def test_infer_text_chat_patches_creates_memory_and_relation_links():
    patches = infer_text_chat_patches(
        source_event_id="evt_chat",
        transcript="2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n",
        person_ids=["person_1", "person_2"],
        relation_id="relation_chat",
    )

    operations = [patch["operation"] for patch in patches]
    memory_patch = next(patch for patch in patches if patch["operation"] == "create_memory")
    link_patch = next(patch for patch in patches if patch["operation"] == "link_entities")
    state_patch = next(patch for patch in patches if patch["operation"] == "update_state")

    assert operations[:2] == ["create_memory", "link_entities"]
    assert memory_patch["payload_json"]["summary"] == "来源于文本聊天导入"
    assert link_patch["payload_json"]["from_id"] == "relation_chat"
    assert link_patch["payload_json"]["relation_type"] == "supported_by_memory"
    assert state_patch["payload_json"]["scope_type"] == "person"
    assert state_patch["payload_json"]["state_type"] == "energy"


def test_infer_email_patches_links_person_to_memory():
    patches = infer_email_patches(source_event_id="evt_email", person_id="person_x", summary="邮件速报")
    assert len(patches) >= 2
    assert patches[0]["operation"] == "create_memory"
    assert patches[0]["payload_json"]["summary"] == "邮件速报"
    assert patches[1]["operation"] == "link_entities"
    assert patches[1]["payload_json"]["from_type"] == "person"
    assert patches[1]["payload_json"]["to_type"] == "memory"


def test_infer_email_patches_can_add_positive_work_state():
    patches = infer_email_patches(
        source_event_id="evt_email_positive",
        person_id="person_x",
        summary="Project Update: 今天的项目推进顺利。",
    )

    state_patch = next(patch for patch in patches if patch["operation"] == "update_state")

    assert state_patch["payload_json"]["scope_type"] == "person"
    assert state_patch["payload_json"]["state_type"] == "work_status"
