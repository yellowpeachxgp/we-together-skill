"""PersonAgent：每个 person 一个独立 agent loop 单元。

设计：
  - 每个 agent 绑定一个 person_id + llm_client
  - 持有私有 context（该 person 视角的 memories）
  - 能 `decide_speak` 判断是否应该发言
  - 能 `speak` 产出一条 response text
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm.client import LLMMessage


@dataclass
class PersonAgent:
    person_id: str
    primary_name: str
    llm_client: object  # LLMClient Protocol
    persona_summary: str | None = None
    style_summary: str | None = None
    private_memories: list[dict] = field(default_factory=list)

    @classmethod
    def from_db(
        cls, db_path: Path, person_id: str, *, llm_client,
        memory_limit: int = 20,
    ) -> "PersonAgent":
        conn = connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT primary_name, persona_summary, style_summary "
            "FROM persons WHERE person_id = ?", (person_id,),
        ).fetchone()
        if row is None:
            conn.close()
            raise ValueError(f"person not found: {person_id}")

        # 私有 memory：perspective_person_id = self OR owner_id = self
        mem_rows = conn.execute(
            """SELECT DISTINCT m.memory_id, m.summary, m.memory_type,
                      m.perspective_person_id, m.relevance_score
               FROM memories m
               LEFT JOIN memory_owners mo ON mo.memory_id = m.memory_id
                 AND mo.owner_type = 'person'
               WHERE m.status = 'active'
                 AND (m.perspective_person_id = ? OR mo.owner_id = ?)
               ORDER BY m.relevance_score DESC
               LIMIT ?""",
            (person_id, person_id, memory_limit),
        ).fetchall()
        conn.close()

        return cls(
            person_id=person_id,
            primary_name=row["primary_name"],
            llm_client=llm_client,
            persona_summary=row["persona_summary"],
            style_summary=row["style_summary"],
            private_memories=[dict(r) for r in mem_rows],
        )

    def build_system_prompt(self, *, scene_summary: str | None = None) -> str:
        lines = [f"你是 {self.primary_name}。"]
        if self.persona_summary:
            lines.append(f"画像：{self.persona_summary}")
        if self.style_summary:
            lines.append(f"说话风格：{self.style_summary}")
        if scene_summary:
            lines.append(f"当前场景：{scene_summary}")
        if self.private_memories:
            lines.append("你记得：")
            for m in self.private_memories[:5]:
                lines.append(f"  - {m['summary']}")
        lines.append("请用第一人称自然说话，不要输出解释或元信息。")
        return "\n".join(lines)

    def speak(
        self, *, scene_summary: str | None = None,
        recent_messages: list[dict] | None = None,
    ) -> str:
        """产出一条回复。recent_messages 是该场景的最近对话。"""
        system_prompt = self.build_system_prompt(scene_summary=scene_summary)
        messages = [LLMMessage(role="system", content=system_prompt)]
        for m in (recent_messages or [])[-10:]:
            role = "assistant" if m.get("speaker") == self.primary_name else "user"
            text = f"[{m.get('speaker', '?')}] {m.get('text', '')}"
            messages.append(LLMMessage(role=role, content=text))
        messages.append(LLMMessage(role="user", content="轮到你了。"))
        resp = self.llm_client.chat(messages)
        return (getattr(resp, "content", None) or "").strip()

    def decide_speak(
        self, *, context: dict, turn_state: dict,
    ) -> float:
        """返回 0..1 的"想说话的意愿"分数。简化版：
        - 当前 scene participant activation_score 为基础
        - 最近是否已发言（刚发言的暂缓）
        - persona 强度（若 persona_summary 含"主动"类词加分）
        """
        score = float(context.get("activation_score", 0.5))
        last_speaker = turn_state.get("last_speaker")
        if last_speaker == self.primary_name:
            score *= 0.3  # 刚说过就缓缓
        persona_text = (self.persona_summary or "").lower()
        for kw, bonus in [("主动", 0.2), ("leader", 0.2), ("话痨", 0.3)]:
            if kw in persona_text:
                score += bonus
        for kw, penalty in [("安静", 0.2), ("内向", 0.2)]:
            if kw in persona_text:
                score -= penalty
        return max(0.0, min(1.0, score))
