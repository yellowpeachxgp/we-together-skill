"""SM-3 Scene scripter：LLM 生成符合 persona 的对话脚本。"""
from __future__ import annotations

from pathlib import Path

from we_together.llm import LLMMessage, get_llm_client
from we_together.runtime.sqlite_retrieval import (
    build_runtime_retrieval_package_from_db,
)


def _build_prompt(pkg: dict, turns: int) -> list[LLMMessage]:
    participants = [
        f"- {p.get('display_name') or p.get('person_id')}: "
        f"{p.get('persona_summary') or '未知 persona'}"
        for p in pkg.get("participants", [])
    ]
    return [
        LLMMessage(role="system",
                    content="你是多人对话剧本作家。严格按 persona 写自然对话。"),
        LLMMessage(role="user",
                    content=(
                        f"场景：{pkg.get('scene_summary', 'unknown')}\n\n"
                        "参与者：\n" + "\n".join(participants) + "\n\n"
                        f"请生成 {turns} 轮对话，JSON 输出: "
                        "{\"script\": [{\"speaker\": str, \"text\": str}]}"
                    )),
    ]


def write_scene_script(
    db_path: Path, *, scene_id: str, turns: int = 6, llm_client=None,
) -> dict:
    client = llm_client or get_llm_client()
    pkg = build_runtime_retrieval_package_from_db(
        db_path=db_path, scene_id=scene_id,
    )
    try:
        payload = client.chat_json(
            _build_prompt(pkg, turns),
            schema_hint={"script": "list"},
        )
    except Exception as exc:
        return {"scene_id": scene_id, "script": [], "error": str(exc)}

    script = list(payload.get("script") or [])
    return {
        "scene_id": scene_id,
        "scene_summary": pkg.get("scene_summary"),
        "script": script,
        "turn_count": len(script),
    }
