"""ProactiveAgent：主动图谱扫描器。

核心职责:
  1. scan(db_path) → 扫描图谱，识别 Trigger
  2. generate_intent(trigger) → LLM 产出 ProactiveIntent
  3. check_budget(intent) → 受 daily_budget 约束
  4. execute(intent) → 落 proactive_intent_event

三类内置 Trigger:
  - AnniversaryTrigger: memory created_at 整数周年
  - SilenceTrigger: person 长期无互动
  - ConflictTrigger: relation_conflict 刚检测到
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm import LLMMessage, get_llm_client
from we_together.services.proactive_prefs import is_allowed

DEFAULT_DAILY_BUDGET = 5


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Trigger:
    name: str
    target_person_id: str
    reason: str
    priority: float = 0.5
    metadata: dict = field(default_factory=dict)


@dataclass
class ProactiveIntent:
    trigger_name: str
    target_person_id: str
    action: str
    text: str
    confidence: float
    reason: str
    metadata: dict = field(default_factory=dict)


def scan_anniversary_triggers(
    db_path: Path, *, anniversary_days: set[int] | None = None,
) -> list[Trigger]:
    days = anniversary_days or {30, 90, 180, 365}
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT m.memory_id, m.summary, m.created_at, mo.owner_id
           FROM memories m
           JOIN memory_owners mo ON mo.memory_id = m.memory_id
           WHERE m.status='active' AND m.relevance_score >= 0.6
             AND mo.owner_type='person'""",
    ).fetchall()
    conn.close()
    now = _now()
    triggers: list[Trigger] = []
    for r in rows:
        try:
            created = datetime.fromisoformat(r["created_at"])
        except (TypeError, ValueError):
            continue
        age_days = (now - created).days
        if age_days in days:
            triggers.append(Trigger(
                name="anniversary",
                target_person_id=r["owner_id"],
                reason=f"memory {r['memory_id']} {age_days} days anniversary",
                priority=0.6,
                metadata={"memory_id": r["memory_id"], "age_days": age_days},
            ))
    return triggers


def scan_silence_triggers(
    db_path: Path, *, silence_days: int = 30,
) -> list[Trigger]:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    cutoff = (_now() - timedelta(days=silence_days)).isoformat()
    rows = conn.execute(
        """SELECT p.person_id, p.primary_name
           FROM persons p
           WHERE p.status='active'
             AND NOT EXISTS (
                 SELECT 1 FROM event_participants ep
                 JOIN events e ON e.event_id=ep.event_id
                 WHERE ep.person_id=p.person_id
                   AND e.timestamp > ?
             )""",
        (cutoff,),
    ).fetchall()
    conn.close()
    return [
        Trigger(
            name="silence", target_person_id=r["person_id"],
            reason=f"{r['primary_name']} 已沉默 >{silence_days} 天",
            priority=0.5, metadata={"days": silence_days},
        ) for r in rows
    ]


def scan_conflict_triggers(db_path: Path) -> list[Trigger]:
    # 简化：查 relation_conflict_service 最近的检测结果无持久化，这里改为
    # 扫 memory_type='conflict_signal' 的 memories（relation_conflict emit_memory 产物）
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT m.memory_id, m.summary, mo.owner_id
           FROM memories m
           JOIN memory_owners mo ON mo.memory_id=m.memory_id
           WHERE m.memory_type='conflict_signal' AND m.status='active'""",
    ).fetchall()
    conn.close()
    return [
        Trigger(
            name="conflict", target_person_id=r["owner_id"],
            reason=f"conflict_signal memory {r['memory_id']}",
            priority=0.8, metadata={"memory_id": r["memory_id"]},
        ) for r in rows
    ]


def scan_all_triggers(db_path: Path) -> list[Trigger]:
    triggers: list[Trigger] = []
    for fn in (scan_anniversary_triggers, scan_silence_triggers, scan_conflict_triggers):
        try:
            triggers.extend(fn(db_path))
        except Exception:
            pass
    # 过滤被 mute / 未 consent 的
    allowed = []
    for t in triggers:
        if is_allowed(db_path, t.target_person_id, t.name):
            allowed.append(t)
    return allowed


def generate_intent(
    trigger: Trigger, *, llm_client=None,
) -> ProactiveIntent:
    client = llm_client or get_llm_client()
    prompt_text = (
        f"触发类型: {trigger.name}\n"
        f"目标 person: {trigger.target_person_id}\n"
        f"原因: {trigger.reason}\n\n"
        "请生成一个温和的主动行为，JSON: "
        "{\"action\": \"send_message|remind|check_in\", "
        "\"text\": \"一句话具体内容\", \"confidence\": 0..1}"
    )
    try:
        payload = client.chat_json(
            [
                LLMMessage(role="system", content="你是图谱主动关怀生成器。"),
                LLMMessage(role="user", content=prompt_text),
            ],
            schema_hint={"action": "str", "text": "str", "confidence": "float"},
        )
    except Exception as exc:
        return ProactiveIntent(
            trigger_name=trigger.name,
            target_person_id=trigger.target_person_id,
            action="noop",
            text=f"[error] {exc}",
            confidence=0.0,
            reason=trigger.reason,
            metadata=trigger.metadata,
        )
    return ProactiveIntent(
        trigger_name=trigger.name,
        target_person_id=trigger.target_person_id,
        action=str(payload.get("action", "check_in")),
        text=str(payload.get("text", "")).strip() or "（无内容）",
        confidence=float(payload.get("confidence") or 0.5),
        reason=trigger.reason,
        metadata=trigger.metadata,
    )


def _count_today_intents(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_type='proactive_intent_event' "
        "AND date(created_at)=date('now')",
    ).fetchone()
    return row[0] or 0


def check_budget(
    db_path: Path, *, daily_budget: int = DEFAULT_DAILY_BUDGET,
) -> int:
    """返回剩余预算。"""
    conn = connect(db_path)
    used = _count_today_intents(conn)
    conn.close()
    return max(0, daily_budget - used)


def execute_intent(db_path: Path, intent: ProactiveIntent) -> str:
    """把 intent 落成 proactive_intent_event。"""
    eid = f"evt_proactive_{uuid.uuid4().hex[:10]}"
    conn = connect(db_path)
    conn.execute(
        """INSERT INTO events(event_id, event_type, source_type, timestamp,
           summary, visibility_level, confidence, is_structured,
           raw_evidence_refs_json, metadata_json, created_at)
           VALUES(?, 'proactive_intent_event', 'proactive_agent', ?, ?,
                  'visible', ?, 1, '[]', ?, ?)""",
        (eid, _now().isoformat(), intent.text, intent.confidence,
         json.dumps({
             "trigger_name": intent.trigger_name,
             "action": intent.action,
             "target_person_id": intent.target_person_id,
             "reason": intent.reason,
             **(intent.metadata or {}),
         }, ensure_ascii=False),
         _now().isoformat()),
    )
    conn.execute(
        "INSERT INTO event_participants(event_id, person_id, participant_role) "
        "VALUES(?, ?, 'target')",
        (eid, intent.target_person_id),
    )
    conn.commit(); conn.close()
    return eid


def proactive_scan(
    db_path: Path,
    *,
    daily_budget: int = DEFAULT_DAILY_BUDGET,
    llm_client=None,
) -> dict:
    triggers = scan_all_triggers(db_path)
    remaining = check_budget(db_path, daily_budget=daily_budget)
    if remaining == 0:
        return {"trigger_count": len(triggers), "executed": 0,
                 "reason": "daily_budget_exhausted"}

    triggers.sort(key=lambda t: t.priority, reverse=True)
    triggers = triggers[:remaining]

    executed: list[dict] = []
    for t in triggers:
        intent = generate_intent(t, llm_client=llm_client)
        if intent.action == "noop":
            continue
        eid = execute_intent(db_path, intent)
        executed.append({
            "event_id": eid, "trigger": t.name,
            "target": t.target_person_id, "action": intent.action,
            "text": intent.text, "confidence": intent.confidence,
        })
    return {
        "trigger_count": len(triggers),
        "executed": len(executed),
        "events": executed,
        "remaining_budget": remaining - len(executed),
    }


def list_recent_intents(db_path: Path, *, limit: int = 20) -> list[dict]:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT event_id, summary, confidence, metadata_json, created_at
           FROM events
           WHERE event_type='proactive_intent_event'
           ORDER BY created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "event_id": r["event_id"],
            "summary": r["summary"],
            "confidence": r["confidence"],
            "metadata": json.loads(r["metadata_json"] or "{}"),
            "created_at": r["created_at"],
        } for r in rows
    ]
