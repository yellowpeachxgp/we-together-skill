"""LLM 驱动的 person facet 增量更新。

读取人物近期事件 → 让 LLM 推理 facets → 通过 upsert_facet patch 落库。

facet_type ∈ {persona, work, life, style, boundary, relationship_pattern}
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm.client import LLMClient, LLMMessage
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


FACET_SCHEMA = {
    "facets": [
        {
            "facet_type": "persona | work | life | style | boundary | relationship_pattern",
            "facet_key": "str (例如 role / hobby / tone)",
            "facet_value": "str",
            "confidence": "float 0..1",
            "reason": "str (来自哪些证据)",
        }
    ]
}


def _fetch_person_recent_events(
    conn: sqlite3.Connection, person_id: str, max_events: int = 20
) -> list[dict]:
    rows = conn.execute(
        """
        SELECT e.event_id, e.summary, e.timestamp, e.event_type
        FROM events e
        JOIN event_participants ep ON ep.event_id = e.event_id
        WHERE ep.person_id = ?
        ORDER BY e.timestamp DESC
        LIMIT ?
        """,
        (person_id, max_events),
    ).fetchall()
    return [
        {
            "event_id": r["event_id"],
            "summary": r["summary"],
            "timestamp": r["timestamp"],
            "event_type": r["event_type"],
        }
        for r in rows
    ]


def _build_extract_prompt(person_name: str, persona: str | None,
                          events: list[dict]) -> list[LLMMessage]:
    bullet_events = "\n".join(
        f"- [{e['timestamp']}] {e['summary']}" for e in events[:10]
    ) or "（暂无事件）"
    return [
        LLMMessage(
            role="system",
            content=(
                "你是社会图谱 facet 抽取器。基于人物的近期事件，推理其稳定面（人格/工作/生活/风格/边界/关系模式）。"
                "严格按 schema 返回，不要发明事件中未体现的特征。"
            ),
        ),
        LLMMessage(
            role="user",
            content=(
                f"人物: {person_name}\n"
                f"已知 persona: {persona or '未知'}\n\n"
                f"近期事件:\n{bullet_events}\n\n"
                "请返回 facets JSON。"
            ),
        ),
    ]


def extract_facets_for_person(
    db_path: Path,
    *,
    person_id: str,
    llm_client: LLMClient,
    max_events: int = 20,
    source_event_id: str | None = None,
) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    person = conn.execute(
        "SELECT person_id, primary_name, persona_summary FROM persons WHERE person_id = ?",
        (person_id,),
    ).fetchone()
    if person is None:
        conn.close()
        raise ValueError(f"Person not found: {person_id}")
    events = _fetch_person_recent_events(conn, person_id, max_events)
    conn.close()

    messages = _build_extract_prompt(
        person["primary_name"], person["persona_summary"], events
    )
    try:
        payload = llm_client.chat_json(messages, schema_hint=FACET_SCHEMA)
    except Exception as exc:
        return {"person_id": person_id, "applied_count": 0, "error": str(exc)}

    facets = payload.get("facets", [])
    applied = 0
    for f in facets:
        ftype = f.get("facet_type")
        fkey = f.get("facet_key")
        if not ftype or not fkey:
            continue
        patch = build_patch(
            source_event_id=source_event_id or f"facet_extract_{person_id}",
            target_type="person_facet",
            target_id=person_id,
            operation="upsert_facet",
            payload={
                "person_id": person_id,
                "facet_type": ftype,
                "facet_key": fkey,
                "facet_value": f.get("facet_value"),
                "confidence": float(f.get("confidence", 0.5)),
                "scope_hint": "llm_extracted",
                "metadata_json": {"reason": f.get("reason")},
            },
            confidence=float(f.get("confidence", 0.5)),
            reason="llm facet extraction",
        )
        apply_patch_record(db_path=db_path, patch=patch)
        applied += 1

    return {"person_id": person_id, "applied_count": applied, "examined_events": len(events)}
