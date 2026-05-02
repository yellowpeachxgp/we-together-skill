"""Claude Skill 适配器。

把 SkillRequest 翻译成 Anthropic Messages API 的形状：
  {system: str, messages: [{role, content}]}

运行时真正的 LLM 调用委派给 we_together.llm 中的 client；此适配器只负责 payload 构造和响应归一化。
"""
from __future__ import annotations

from we_together.llm.client import LLMClient, LLMMessage
from we_together.runtime.skill_runtime import SkillRequest, SkillResponse


class ClaudeSkillAdapter:
    name = "claude"

    def build_payload(self, request: SkillRequest) -> dict:
        payload = {
            "system": request.system_prompt,
            "messages": [dict(m) for m in request.messages],
            "metadata": {
                "scene_id": request.scene_id,
                "source": "we_together",
                **request.metadata,
            },
        }
        if request.tools:
            payload["tools"] = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("input_schema", {"type": "object", "properties": {}}),
                }
                for t in request.tools
            ]
        return payload

    def invoke(
        self,
        request: SkillRequest,
        llm_client: LLMClient,
        **llm_kwargs,
    ) -> SkillResponse:
        llm_messages: list[LLMMessage] = [
            LLMMessage(role="system", content=request.system_prompt)
        ]
        for m in request.messages:
            llm_messages.append(LLMMessage(role=m["role"], content=m["content"]))
        resp = llm_client.chat(llm_messages, **llm_kwargs)
        policy = request.retrieval_package.get("response_policy", {})
        return SkillResponse(
            text=resp.content,
            speaker_person_id=policy.get("primary_speaker"),
            supporting_speakers=list(policy.get("supporting_speakers", [])),
            usage=resp.usage,
            raw={"adapter": self.name, **resp.raw},
        )
