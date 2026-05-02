"""autonomous_agent（Phase 52 AG）：让 agent 基于内在驱动力自主决定行动。

核心循环：
1. compute_drives(db, person_id) → 根据近期 memory / trace / state 推出当前 drive
2. decide_action(drives) → 选出最迫切 drive → 生成 action
3. record_autonomous_action(db, ...) 留痕（不变式 #27）

不变式 #27：Agent 自主行为必须可解释——每次 action 必须能追溯到 drive + 来源 memory/trace。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Drive:
    drive_id: str
    person_id: str
    drive_type: str
    intensity: float
    source_memory_ids: list[str] = field(default_factory=list)
    source_event_ids: list[str] = field(default_factory=list)
    status: str = "active"

    def to_dict(self) -> dict:
        return {
            "drive_id": self.drive_id, "person_id": self.person_id,
            "drive_type": self.drive_type, "intensity": self.intensity,
            "source_memory_ids": list(self.source_memory_ids),
            "source_event_ids": list(self.source_event_ids),
            "status": self.status,
        }


DRIVE_RULES = {
    # 关键词 → drive_type，intensity 权重
    "connection": ["想念", "联系", "见面", "见一面", "聊聊"],
    "curiosity": ["好奇", "想知道", "是不是", "为什么"],
    "resolve": ["担心", "没解决", "待办", "纠结", "冲突"],
    "obligation": ["答应", "承诺", "deadline", "必须"],
    "rest": ["累", "疲惫", "休息", "睡"],
}


def _detect_drives_from_text(text: str) -> list[tuple[str, float]]:
    """极简关键词触发。生产中由 LLM 分析。"""
    if not text:
        return []
    out: list[tuple[str, float]] = []
    lower = text.lower()
    for drive, kws in DRIVE_RULES.items():
        hits = sum(1 for k in kws if k in lower or k in text)
        if hits > 0:
            out.append((drive, min(1.0, 0.3 + 0.2 * hits)))
    return out


def compute_drives(
    db_path: Path, person_id: str, *, lookback_days: int = 14,
) -> list[Drive]:
    """从近期 memory 和 event 启发式地推出 drive。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    drives: dict[str, Drive] = {}
    try:
        # 近期 memory
        memories = conn.execute(
            """SELECT m.memory_id, m.summary FROM memories m
               JOIN memory_owners mo ON mo.memory_id=m.memory_id
               WHERE mo.owner_type='person' AND mo.owner_id=?
                 AND m.status='active'
                 AND m.updated_at >= datetime('now', ?)
               ORDER BY m.updated_at DESC LIMIT 30""",
            (person_id, f"-{int(lookback_days)} days"),
        ).fetchall()
        # 近期 event (经 event_participants)
        events = conn.execute(
            """SELECT e.event_id, e.summary FROM events e
               JOIN event_participants ep ON ep.event_id=e.event_id
               WHERE ep.person_id=? AND e.timestamp >= datetime('now', ?)
               ORDER BY e.timestamp DESC LIMIT 30""",
            (person_id, f"-{int(lookback_days)} days"),
        ).fetchall()

        for row in memories:
            hits = _detect_drives_from_text(row["summary"])
            for drive_type, intensity in hits:
                d = drives.get(drive_type)
                if d is None:
                    did = f"drive_{uuid.uuid4().hex[:10]}"
                    d = Drive(
                        drive_id=did, person_id=person_id,
                        drive_type=drive_type, intensity=intensity,
                    )
                    drives[drive_type] = d
                else:
                    d.intensity = min(1.0, d.intensity + 0.1)
                d.source_memory_ids.append(row["memory_id"])

        for row in events:
            hits = _detect_drives_from_text(row["summary"])
            for drive_type, intensity in hits:
                d = drives.get(drive_type)
                if d is None:
                    did = f"drive_{uuid.uuid4().hex[:10]}"
                    d = Drive(
                        drive_id=did, person_id=person_id,
                        drive_type=drive_type, intensity=intensity * 0.8,
                    )
                    drives[drive_type] = d
                else:
                    d.intensity = min(1.0, d.intensity + 0.05)
                d.source_event_ids.append(row["event_id"])
    finally:
        conn.close()
    return sorted(drives.values(), key=lambda d: -d.intensity)


def persist_drives(db_path: Path, drives: list[Drive]) -> int:
    if not drives:
        return 0
    conn = sqlite3.connect(db_path)
    try:
        for d in drives:
            conn.execute(
                """INSERT OR REPLACE INTO agent_drives(drive_id, person_id,
                   drive_type, intensity, source_memory_ids_json, source_event_ids_json,
                   status, activated_at, metadata_json)
                   VALUES(?, ?, ?, ?, ?, ?, 'active', datetime('now'), '{}')""",
                (d.drive_id, d.person_id, d.drive_type, d.intensity,
                 json.dumps(d.source_memory_ids, ensure_ascii=False),
                 json.dumps(d.source_event_ids, ensure_ascii=False)),
            )
        conn.commit()
    finally:
        conn.close()
    return len(drives)


@dataclass
class Intent:
    action_type: str
    reason: str
    target_person_id: str | None = None
    drive_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type, "reason": self.reason,
            "target_person_id": self.target_person_id,
            "drive_id": self.drive_id,
        }


def decide_action(drives: list[Drive], *, threshold: float = 0.5) -> Intent | None:
    """选最强 drive → 产生 Intent。不调 LLM。"""
    if not drives:
        return None
    top = drives[0]
    if top.intensity < threshold:
        return None
    action_map = {
        "connection": ("reach_out", "想联系对方"),
        "curiosity": ("inquire", "对某事好奇"),
        "resolve": ("confront", "需要处理未解决的事"),
        "obligation": ("fulfill", "有承诺要兑现"),
        "rest": ("withdraw", "需要休息"),
    }
    action_type, reason = action_map.get(
        top.drive_type, ("reflect", f"处理 {top.drive_type} 驱动"),
    )
    return Intent(
        action_type=action_type, reason=reason,
        drive_id=top.drive_id,
    )


def record_autonomous_action(
    db_path: Path, *,
    person_id: str, action_type: str,
    triggered_by_drive_id: str | None = None,
    triggered_by_memory_id: str | None = None,
    triggered_by_trace_id: int | None = None,
    output_event_id: str | None = None,
    rationale: str | None = None,
) -> int:
    if not any([triggered_by_drive_id, triggered_by_memory_id, triggered_by_trace_id]):
        raise ValueError(
            "不变式 #27: 自主行为必须能追溯到 drive / memory / trace 至少一个"
        )
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """INSERT INTO autonomous_actions(person_id, action_type,
               triggered_by_drive_id, triggered_by_memory_id, triggered_by_trace_id,
               output_event_id, rationale, created_at)
               VALUES(?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (person_id, action_type, triggered_by_drive_id, triggered_by_memory_id,
             triggered_by_trace_id, output_event_id, rationale),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_autonomous_actions(db_path: Path, person_id: str, limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT action_id, action_type, triggered_by_drive_id,
               triggered_by_memory_id, triggered_by_trace_id, rationale, created_at
               FROM autonomous_actions WHERE person_id=?
               ORDER BY created_at DESC LIMIT ?""",
            (person_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
