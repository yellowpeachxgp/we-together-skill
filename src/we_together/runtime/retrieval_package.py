def build_runtime_retrieval_package(
    scene: dict,
    environment: dict,
    participants: list,
    active_relations: list,
    relevant_memories: list,
    current_states: list,
    activation_map: list,
    response_policy: dict,
) -> dict:
    return {
        "scene_summary": scene,
        "environment_constraints": environment,
        "participants": participants,
        "active_relations": active_relations,
        "relevant_memories": relevant_memories,
        "current_states": current_states,
        "activation_map": activation_map,
        "response_policy": response_policy,
        "safety_and_budget": {},
    }
