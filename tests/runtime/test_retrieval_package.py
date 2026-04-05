from we_together.domain.enums import ActivationState, ResponseMode
from we_together.runtime.retrieval_package import build_runtime_retrieval_package


def test_activation_and_response_enums_have_expected_values():
    assert ActivationState.LATENT.value == "latent"
    assert ResponseMode.SINGLE_PRIMARY.value == "single_primary"


def test_build_runtime_retrieval_package_contains_required_sections():
    package = build_runtime_retrieval_package(
        scene={"scene_id": "scene_1", "scene_type": "private_chat", "summary": "late night chat"},
        environment={"location_scope": "remote", "channel_scope": "private_dm"},
        participants=[],
        active_relations=[],
        relevant_memories=[],
        current_states=[],
        activation_map=[],
        response_policy={"mode": "single_primary"},
    )

    assert "scene_summary" in package
    assert "environment_constraints" in package
    assert "participants" in package
    assert "response_policy" in package
