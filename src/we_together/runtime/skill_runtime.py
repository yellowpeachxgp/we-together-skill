"""SkillRuntime 协议：把社会图谱 retrieval_package 与 user 输入 抽象为与宿主无关的请求/响应。

原则：
- 不依赖任何 LLM SDK
- 不依赖任何 Skill 宿主 API 形状
- 所有字段可序列化（dict / JSON）
- adapters/ 目录下的具体适配器负责把 SkillRequest 翻译为各宿主所需格式

自 v0.14.0（Phase 33 / ADR 0034）起，SkillRequest/Response 新增 schema_version 字段，默认 "1"。
破坏性变更需要 v2，而不是 in-place 改字段（不变式 #19）。
"""
from __future__ import annotations

from dataclasses import dataclass, field

SKILL_SCHEMA_VERSION = "1"


@dataclass
class SkillRequest:
    system_prompt: str
    messages: list[dict]  # [{role, content}]
    retrieval_package: dict
    scene_id: str
    user_input: str
    metadata: dict = field(default_factory=dict)
    tools: list[dict] = field(default_factory=list)
    schema_version: str = SKILL_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "system_prompt": self.system_prompt,
            "messages": list(self.messages),
            "retrieval_package": self.retrieval_package,
            "scene_id": self.scene_id,
            "user_input": self.user_input,
            "metadata": dict(self.metadata),
            "tools": [dict(t) for t in self.tools],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillRequest":
        version = data.get("schema_version", SKILL_SCHEMA_VERSION)
        if version != SKILL_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported SkillRequest schema_version={version}; "
                f"this runtime speaks v{SKILL_SCHEMA_VERSION}"
            )
        return cls(
            system_prompt=data["system_prompt"],
            messages=list(data.get("messages", [])),
            retrieval_package=dict(data.get("retrieval_package", {})),
            scene_id=data.get("scene_id", ""),
            user_input=data.get("user_input", ""),
            metadata=dict(data.get("metadata", {})),
            tools=list(data.get("tools", [])),
            schema_version=version,
        )


@dataclass
class SkillResponse:
    text: str
    speaker_person_id: str | None = None
    supporting_speakers: list[str] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)
    schema_version: str = SKILL_SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "text": self.text,
            "speaker_person_id": self.speaker_person_id,
            "supporting_speakers": list(self.supporting_speakers),
            "usage": dict(self.usage),
            "raw": dict(self.raw),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SkillResponse":
        version = data.get("schema_version", SKILL_SCHEMA_VERSION)
        if version != SKILL_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported SkillResponse schema_version={version}; "
                f"this runtime speaks v{SKILL_SCHEMA_VERSION}"
            )
        return cls(
            text=data.get("text", ""),
            speaker_person_id=data.get("speaker_person_id"),
            supporting_speakers=list(data.get("supporting_speakers", [])),
            usage=dict(data.get("usage", {})),
            raw=dict(data.get("raw", {})),
            schema_version=version,
        )
