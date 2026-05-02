"""SM-1 What-if 模拟器：给定当前图谱 + 假设事件，LLM 产出未来 30 天可能的变化。

输入:
  - scene_id: 作为 retrieval 入口
  - hypothesis: 假设文本 (如 "Alice 离职")

输出:
  {
    "hypothesis": str,
    "predictions": [{"horizon_days": int, "prediction": str, "affected_entities": [...]}],
    "confidence": float
  }

不修改图谱，只产出推演报告。
"""
from __future__ import annotations

from pathlib import Path

from we_together.llm import LLMMessage, get_llm_client
from we_together.runtime.sqlite_retrieval import (
    build_runtime_retrieval_package_from_db,
)


def _build_prompt(pkg: dict, hypothesis: str) -> list[LLMMessage]:
    participants = [p.get("display_name") or p.get("person_id")
                    for p in pkg.get("participants", [])]
    relations = [f"{r.get('core_type')}({r.get('strength', 0):.2f})"
                 for r in pkg.get("active_relations", [])]
    return [
        LLMMessage(
            role="system",
            content=(
                "你是社会推演器。基于现有图谱和一个假设事件，预测未来 30 天可能发生的变化。"
                "严格基于给定信息，不臆造人物或关系。"
            ),
        ),
        LLMMessage(
            role="user",
            content=(
                f"场景：{pkg.get('scene_summary', 'unknown')}\n"
                f"参与者：{', '.join(participants)}\n"
                f"活跃关系：{', '.join(relations)}\n\n"
                f"假设事件：{hypothesis}\n\n"
                "请输出 JSON: {\"predictions\": ["
                "{\"horizon_days\": int, \"prediction\": str, \"affected_entities\": list}"
                "], \"confidence\": 0..1}"
            ),
        ),
    ]


def simulate_what_if(
    db_path: Path,
    *,
    scene_id: str,
    hypothesis: str,
    llm_client=None,
) -> dict:
    client = llm_client or get_llm_client()
    pkg = build_runtime_retrieval_package_from_db(
        db_path=db_path, scene_id=scene_id,
    )
    try:
        payload = client.chat_json(
            _build_prompt(pkg, hypothesis),
            schema_hint={"predictions": "list", "confidence": "float"},
        )
    except Exception as exc:
        return {
            "hypothesis": hypothesis,
            "error": str(exc),
            "predictions": [],
            "confidence": 0.0,
            "mock_mode": True,
        }

    predictions = list(payload.get("predictions") or [])
    confidence = float(payload.get("confidence") or 0.0)

    # Mock fallback：LLM 未返回 predictions key 时给占位
    provider = getattr(client, "provider", "") or ""
    mock_mode = provider == "mock" and not predictions
    if mock_mode:
        predictions = [{
            "horizon_days": 30,
            "prediction": (
                "（mock 模式占位）当前 WE_TOGETHER_LLM_PROVIDER=mock，"
                "未产出实际推演。请设置真实 provider（anthropic / openai_compat）。"
            ),
            "affected_entities": [],
        }]

    return {
        "hypothesis": hypothesis,
        "scene_id": scene_id,
        "predictions": predictions,
        "confidence": confidence,
        "mock_mode": mock_mode,
    }
