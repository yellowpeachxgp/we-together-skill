"""LLM-as-judge：让另一 LLM 打分 condenser/drift 输出的忠实度。"""
from __future__ import annotations

from we_together.llm import LLMMessage


def build_fidelity_prompt(
    sources: list[str], summary: str,
) -> list[LLMMessage]:
    bullets = "\n".join(f"- {s}" for s in sources[:10])
    return [
        LLMMessage(role="system", content="你是内容忠实度评审员。"),
        LLMMessage(
            role="user",
            content=(
                f"源材料：\n{bullets}\n\n摘要：{summary}\n\n"
                "请输出 JSON: {\"fidelity_score\": 0..1, \"missing_points\": [..], \"fabrications\": [..]}"
            ),
        ),
    ]


def judge_fidelity(
    sources: list[str], summary: str, *, llm_client,
) -> dict:
    payload = llm_client.chat_json(
        build_fidelity_prompt(sources, summary),
        schema_hint={"fidelity_score": "float", "missing_points": "list", "fabrications": "list"},
    )
    return {
        "fidelity_score": float(payload.get("fidelity_score") or 0.0),
        "missing_points": list(payload.get("missing_points") or []),
        "fabrications": list(payload.get("fabrications") or []),
    }
