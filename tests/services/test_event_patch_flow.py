from we_together.services.patch_service import build_patch


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
