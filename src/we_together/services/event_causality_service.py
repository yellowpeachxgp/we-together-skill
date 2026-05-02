"""Event causality：LLM 推理事件因果链 A → B。"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm import LLMMessage, get_llm_client


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _fetch_recent_events(conn: sqlite3.Connection, limit: int) -> list[dict]:
    rows = conn.execute(
        """SELECT event_id, event_type, summary, timestamp
           FROM events
           WHERE summary IS NOT NULL AND summary != ''
           ORDER BY timestamp DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    return [{"event_id": r[0], "event_type": r[1], "summary": r[2], "timestamp": r[3]}
            for r in rows]


def _build_prompt(events: list[dict]) -> list[LLMMessage]:
    bullets = "\n".join(f"- [{e['event_id']}] {e['summary']}" for e in events[:15])
    return [
        LLMMessage(role="system", content="你是事件因果推理器。只输出可信的因果边。"),
        LLMMessage(
            role="user",
            content=(
                f"以下是最近事件：\n{bullets}\n\n"
                "请输出 JSON: {\"edges\": [{\"cause\": eid, \"effect\": eid, \"reason\": \"\", \"confidence\": 0..1}]}"
            ),
        ),
    ]


def infer_event_causality(
    db_path: Path, *, limit: int = 15, llm_client=None,
) -> dict:
    client = llm_client or get_llm_client()
    conn = connect(db_path)
    events = _fetch_recent_events(conn, limit)
    conn.close()
    if len(events) < 2:
        return {"created_count": 0, "edges": []}

    try:
        payload = client.chat_json(
            _build_prompt(events),
            schema_hint={"edges": "list"},
        )
    except Exception as exc:
        return {"created_count": 0, "error": str(exc)}

    created: list[dict] = []
    conn = connect(db_path)
    now = _now()
    for edge in payload.get("edges", []) or []:
        cause = edge.get("cause")
        effect = edge.get("effect")
        if not cause or not effect or cause == effect:
            continue
        edge_id = f"ec_{uuid.uuid4().hex[:12]}"
        try:
            conn.execute(
                """INSERT OR IGNORE INTO event_causality(
                    edge_id, cause_event_id, effect_event_id, confidence,
                    reason, source, created_at
                ) VALUES(?,?,?,?,?,?,?)""",
                (edge_id, cause, effect, edge.get("confidence") or 0.5,
                 edge.get("reason") or "", "llm", now),
            )
            created.append({"edge_id": edge_id, "cause": cause, "effect": effect})
        except sqlite3.Error:
            continue
    conn.commit()
    conn.close()
    return {"created_count": len(created), "edges": created}


def list_causality(db_path: Path, *, limit: int = 50) -> list[dict]:
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT edge_id, cause_event_id, effect_event_id, confidence, reason, source "
        "FROM event_causality ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {"edge_id": r[0], "cause": r[1], "effect": r[2],
         "confidence": r[3], "reason": r[4], "source": r[5]}
        for r in rows
    ]
