"""multi_agent_dialogue（Phase 46 MA-2/3/4/7/9）：扩展 turn_taking 以支持：

- **互听**：agent.speak 会收到前 N 轮 transcript（通过 recent_messages 参数）
- **打断**：interrupt_threshold 让高分 agent 可抢占
- **私聊 vs 公开**：audience=list 指定谁能听见
- **transcript → event**：一次对话会作为 dialogue_event 写入 events 表
- **scene memory 同步**：对话后调 scene_service 做 memory annotation（可选）
"""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from we_together.agents.person_agent import PersonAgent
from we_together.agents.turn_taking import next_speaker


@dataclass
class TranscriptEntry:
    speaker: str           # primary_name
    speaker_id: str        # person_id
    text: str
    audience: list[str] = field(default_factory=list)    # [] = 公开
    is_interrupt: bool = False
    turn_index: int = 0

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker, "speaker_id": self.speaker_id,
            "text": self.text, "audience": list(self.audience),
            "is_interrupt": self.is_interrupt, "turn_index": self.turn_index,
        }


def _visible_messages_for(
    agent: PersonAgent, transcript: list[TranscriptEntry],
) -> list[dict]:
    """agent 能看到的历史：公开消息 + 自己参与的私聊。"""
    out: list[dict] = []
    for e in transcript:
        if not e.audience:
            out.append({"speaker": e.speaker, "text": e.text})
        elif agent.person_id in e.audience or agent.primary_name in e.audience:
            out.append({"speaker": e.speaker, "text": e.text, "private": True})
        elif agent.person_id == e.speaker_id:
            out.append({"speaker": e.speaker, "text": e.text, "private": True})
    return out


def orchestrate_dialogue(
    agents: list[PersonAgent], *,
    scene_summary: str,
    activation_map: dict[str, dict],
    turns: int = 5,
    interrupt_threshold: float = 0.85,
    private_turn_map: dict[int, list[str]] | None = None,
) -> dict:
    """运行多轮多 agent 对话，支持互听 + 打断 + 私聊。

    private_turn_map: {turn_index: [audience_person_ids]} — 指定某些轮次是私聊
    interrupt_threshold: 某轮前 decide_speak >= 该阈值的非当前 speaker 可"打断"
    """
    private_turn_map = private_turn_map or {}
    transcript: list[TranscriptEntry] = []
    turn_state: dict[str, Any] = {
        "last_speaker": None, "history": [], "interrupts": 0,
    }

    for turn in range(turns):
        # 打断检查：上轮发生后，是否有非 last_speaker 的 agent 分数 ≥ threshold？
        interrupt_candidate: PersonAgent | None = None
        for a in agents:
            if a.primary_name == turn_state["last_speaker"]:
                continue
            score = a.decide_speak(
                context=activation_map.get(a.person_id, {"activation_score": 0.5}),
                turn_state=turn_state,
            )
            if score >= interrupt_threshold:
                interrupt_candidate = a
                break

        speaker: PersonAgent | None
        is_interrupt = False
        if interrupt_candidate is not None:
            speaker = interrupt_candidate
            is_interrupt = True
            turn_state["interrupts"] += 1
        else:
            speaker = next_speaker(
                agents, activation_map=activation_map, turn_state=turn_state,
            )
        if speaker is None:
            break

        recent_visible = _visible_messages_for(speaker, transcript)
        text = speaker.speak(
            scene_summary=scene_summary,
            recent_messages=recent_visible,
        )
        entry = TranscriptEntry(
            speaker=speaker.primary_name,
            speaker_id=speaker.person_id,
            text=text,
            audience=list(private_turn_map.get(turn, [])),
            is_interrupt=is_interrupt,
            turn_index=turn,
        )
        transcript.append(entry)
        turn_state["last_speaker"] = speaker.primary_name
        turn_state["history"].append(entry.to_dict())

    return {
        "transcript": [e.to_dict() for e in transcript],
        "turns_taken": len(transcript),
        "interrupts": turn_state["interrupts"],
    }


def record_transcript_as_event(
    db_path: Path, *,
    scene_id: str | None,
    transcript: list[dict],
    summary_override: str | None = None,
) -> str:
    """把一份 transcript 作为 dialogue_event 写入 events 表。"""
    import json
    ev_id = f"evt_dialogue_{uuid.uuid4().hex[:10]}"
    summary = summary_override or (
        f"{len(transcript)} agent turns in scene {scene_id or '(none)'}"
    )
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO events(event_id, event_type, source_type, timestamp,
               summary, visibility_level, confidence, is_structured,
               raw_evidence_refs_json, metadata_json, created_at)
               VALUES(?, 'dialogue_event', 'multi_agent_dialogue', datetime('now'),
               ?, 'visible', 0.9, 1, '[]', ?, datetime('now'))""",
            (ev_id, summary,
             json.dumps({"transcript": transcript, "scene_id": scene_id},
                         ensure_ascii=False)),
        )
        if scene_id:
            conn.execute(
                "UPDATE events SET scene_id=? WHERE event_id=?",
                (scene_id, ev_id),
            )
        conn.commit()
    finally:
        conn.close()
    return ev_id
