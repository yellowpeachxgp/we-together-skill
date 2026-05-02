"""Turn-taking scheduler：多 agent 场景下决定下一个发言者。"""
from __future__ import annotations

from we_together.agents.person_agent import PersonAgent


def compute_turn_priority(
    agent: PersonAgent,
    *,
    context: dict,
    turn_state: dict,
) -> float:
    return agent.decide_speak(context=context, turn_state=turn_state)


def next_speaker(
    agents: list[PersonAgent],
    *,
    activation_map: dict[str, dict],
    turn_state: dict,
) -> PersonAgent | None:
    """按 decide_speak 分数选最高；相同分数按 person_id 字典序。"""
    if not agents:
        return None
    scored: list[tuple[float, str, PersonAgent]] = []
    for a in agents:
        ctx = activation_map.get(a.person_id, {"activation_score": 0.5})
        score = compute_turn_priority(a, context=ctx, turn_state=turn_state)
        scored.append((score, a.person_id, a))
    scored.sort(key=lambda x: (-x[0], x[1]))
    top_score = scored[0][0]
    if top_score <= 0.0:
        return None
    return scored[0][2]


def orchestrate_multi_agent_turn(
    agents: list[PersonAgent],
    *,
    scene_summary: str,
    activation_map: dict[str, dict],
    turns: int = 5,
) -> list[dict]:
    """运行 N 轮多 agent 对话，返回 [{speaker, text}, ...]。"""
    transcript: list[dict] = []
    turn_state: dict = {"last_speaker": None, "history": []}
    for _ in range(turns):
        speaker = next_speaker(agents, activation_map=activation_map, turn_state=turn_state)
        if speaker is None:
            break
        text = speaker.speak(
            scene_summary=scene_summary,
            recent_messages=transcript,
        )
        entry = {"speaker": speaker.primary_name, "text": text}
        transcript.append(entry)
        turn_state["last_speaker"] = speaker.primary_name
        turn_state["history"].append(entry)
    return transcript
