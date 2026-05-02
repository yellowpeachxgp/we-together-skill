"""Persona drift 服务：基于 window 内 events 让 LLM 重新蒸馏 persona_summary。

对每个 active person：
  1. 取最近 window_days 的 events（该 person 参与的）
  2. 若事件 >= min_events，调用 LLM 产出新 persona_summary / style_summary
  3. 若与原 summary 不同，走 update_entity patch

LLM 不可用时退化：为空或抛异常时保持原 summary 不变。
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm import LLMMessage, get_llm_client
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


def _fetch_person_events(
    conn: sqlite3.Connection, person_id: str, window_start: datetime
) -> list[str]:
    rows = conn.execute(
        """
        SELECT e.summary
        FROM events e
        JOIN event_participants ep ON ep.event_id = e.event_id
        WHERE ep.person_id = ?
          AND (e.timestamp IS NULL OR e.timestamp >= ?)
          AND e.summary IS NOT NULL AND e.summary != ''
        ORDER BY e.timestamp DESC
        LIMIT 50
        """,
        (person_id, window_start.isoformat()),
    ).fetchall()
    return [r[0] for r in rows]


def _build_prompt(name: str, existing: str | None, events: list[str]) -> list[LLMMessage]:
    bullets = "\n".join(f"- {e}" for e in events[:20])
    return [
        LLMMessage(role="system", content="你是人物画像助手，基于事件更新一句话的 persona_summary。"),
        LLMMessage(
            role="user",
            content=(
                f"人物：{name}\n原画像：{existing or '（空）'}\n"
                f"近期事件：\n{bullets}\n"
                "请输出 JSON: {\"persona_summary\": \"一句话\", \"style_summary\": \"一句话\"}"
            ),
        ),
    ]


def drift_personas(
    db_path: Path,
    *,
    window_days: int = 30,
    min_events: int = 3,
    person_ids: list[str] | None = None,
    llm_client=None,
    source_event_id: str | None = None,
) -> dict:
    window_start = datetime.now(UTC) - timedelta(days=window_days)
    client = llm_client or get_llm_client()

    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    if person_ids:
        q = "SELECT person_id, primary_name, persona_summary, style_summary FROM persons " \
            "WHERE status = 'active' AND person_id IN (%s)" % ",".join("?" for _ in person_ids)
        rows = conn.execute(q, tuple(person_ids)).fetchall()
    else:
        rows = conn.execute(
            "SELECT person_id, primary_name, persona_summary, style_summary FROM persons "
            "WHERE status = 'active'"
        ).fetchall()

    updates: list[dict] = []
    for row in rows:
        pid = row["person_id"]
        events = _fetch_person_events(conn, pid, window_start)
        if len(events) < min_events:
            continue
        try:
            payload = client.chat_json(
                _build_prompt(row["primary_name"], row["persona_summary"], events),
                schema_hint={"persona_summary": "str", "style_summary": "str"},
            )
        except Exception:
            continue
        new_persona = str(payload.get("persona_summary", "") or "").strip()
        new_style = str(payload.get("style_summary", "") or "").strip()
        if not new_persona and not new_style:
            continue
        patch_payload: dict = {}
        if new_persona and new_persona != (row["persona_summary"] or ""):
            patch_payload["persona_summary"] = new_persona
        if new_style and new_style != (row["style_summary"] or ""):
            patch_payload["style_summary"] = new_style
        if not patch_payload:
            continue
        updates.append({"person_id": pid, "payload": patch_payload, "events_used": len(events)})

    conn.close()

    for u in updates:
        patch = build_patch(
            source_event_id=source_event_id or f"persona_drift_{u['person_id']}",
            target_type="person",
            target_id=u["person_id"],
            operation="update_entity",
            payload=u["payload"],
            confidence=0.55,
            reason=f"persona drift from {u['events_used']} events",
        )
        apply_patch_record(db_path=db_path, patch=patch)
        # 写 persona_history（Phase 15 TL-1）
        try:
            from we_together.services.persona_history_service import record_persona_change
            record_persona_change(
                db_path,
                person_id=u["person_id"],
                persona_summary=u["payload"].get("persona_summary"),
                style_summary=u["payload"].get("style_summary"),
                source_reason=f"drift from {u['events_used']} events",
                confidence=0.55,
            )
        except Exception:
            pass

    return {"drifted_count": len(updates), "window_days": window_days, "details": updates}
