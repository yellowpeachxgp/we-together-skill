"""OpenAI Chat Completions 兼容适配器。

把 SkillRequest 翻译成 {messages: [{role: system/user/assistant, content}]}，
system 作为第一条 message。
"""
from __future__ import annotations

from we_together.llm.client import LLMClient, LLMMessage
from we_together.runtime.skill_runtime import SkillRequest, SkillResponse


class OpenAISkillAdapter:
    name = "openai_compat"

    def build_payload(self, request: SkillRequest) -> dict:
        messages = [{"role": "system", "content": request.system_prompt}]
        for m in request.messages:
            messages.append(dict(m))
        payload = {
            "messages": messages,
            "metadata": {
                "scene_id": request.scene_id,
                **request.metadata,
            },
        }
        if request.tools:
            # OpenAI function schema: {type: "function", function: {name, description, parameters}}
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t.get("input_schema", {"type": "object", "properties": {}}),
                    },
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
