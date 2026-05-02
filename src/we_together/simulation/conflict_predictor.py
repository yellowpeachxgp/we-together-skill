"""SM-2 Conflict predictor：基于 relation_conflict 向前推演 7/30 天冲突概率。"""
from __future__ import annotations

from pathlib import Path

from we_together.llm import LLMMessage, get_llm_client
from we_together.services.relation_conflict_service import detect_relation_conflicts


def _build_prompt(conflicts: list[dict]) -> list[LLMMessage]:
    lines = [f"- relation={c['relation_id']}, reversals={c['reversals']}, "
             f"pos={c['positive_count']} neg={c['negative_count']}"
             for c in conflicts[:10]]
    return [
        LLMMessage(role="system",
                    content="你是关系冲突预测器。基于近期反转历史，预测未来 7/30 天是否会爆发显性冲突。"),
        LLMMessage(role="user",
                    content=(
                        "近期 relation conflict 候选：\n" + "\n".join(lines) + "\n\n"
                        "请输出 JSON: {\"predictions\": ["
                        "{\"relation_id\": str, \"horizon_days\": 7 或 30, "
                        "\"probability\": 0..1, \"reason\": str}]}"
                    )),
    ]


def predict_conflicts(
    db_path: Path, *, window_days: int = 30, llm_client=None,
) -> dict:
    conflicts = detect_relation_conflicts(db_path, window_days=window_days,
                                           min_reversals=1)
    if conflicts["conflict_count"] == 0:
        return {"prediction_count": 0, "predictions": [],
                 "reason": "no_conflict_history"}

    client = llm_client or get_llm_client()
    try:
        payload = client.chat_json(
            _build_prompt(conflicts["details"]),
            schema_hint={"predictions": "list"},
        )
    except Exception as exc:
        return {"prediction_count": 0, "predictions": [], "error": str(exc)}

    predictions = list(payload.get("predictions") or [])
    return {
        "prediction_count": len(predictions),
        "predictions": predictions,
        "base_conflict_count": conflicts["conflict_count"],
    }
