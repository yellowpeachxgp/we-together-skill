"""Narrative arc 服务：把相关 events 聚合成章节。

LLM 驱动：给定近 N 个 events，让 LLM 返回 {arcs: [{title, theme, summary,
event_ids}]}。每个 arc 写 narrative_arcs + narrative_arc_events。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm import LLMMessage, get_llm_client


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _fetch_recent_events(
    conn: sqlite3.Connection, *, scene_id: str | None, limit: int,
) -> list[dict]:
    if scene_id:
        rows = conn.execute(
            "SELECT event_id, summary, timestamp FROM events "
            "WHERE scene_id = ? AND summary IS NOT NULL AND summary != '' "
            "ORDER BY timestamp DESC LIMIT ?",
            (scene_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT event_id, summary, timestamp FROM events "
            "WHERE summary IS NOT NULL AND summary != '' "
            "ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"event_id": r[0], "summary": r[1], "timestamp": r[2]} for r in rows]


def _build_prompt(events: list[dict]) -> list[LLMMessage]:
    bullets = "\n".join(f"- [{e['event_id']}] {e['summary']}" for e in events[:30])
    return [
        LLMMessage(role="system",
                    content="你是故事聚合器。把相关事件合成若干'章节'，每章对应一个主题。"),
        LLMMessage(role="user",
                    content=(
                        "最近事件：\n" + bullets + "\n\n"
                        "请输出 JSON: {\"arcs\": ["
                        "{\"title\": str, \"theme\": str, \"summary\": str, "
                        "\"event_ids\": [eid, ...]}"
                        "]}"
                    )),
    ]


def aggregate_narrative_arcs(
    db_path: Path, *, scene_id: str | None = None, limit: int = 20, llm_client=None,
) -> dict:
    client = llm_client or get_llm_client()
    conn = connect(db_path)
    events = _fetch_recent_events(conn, scene_id=scene_id, limit=limit)
    if len(events) < 2:
        conn.close()
        return {"arc_count": 0, "arcs": []}

    try:
        payload = client.chat_json(
            _build_prompt(events),
            schema_hint={"arcs": "list"},
        )
    except Exception as exc:
        conn.close()
        return {"arc_count": 0, "error": str(exc)}

    arcs = list(payload.get("arcs") or [])
    created: list[dict] = []
    now = _now()
    for arc in arcs:
        arc_id = f"arc_{uuid.uuid4().hex[:12]}"
        event_ids = list(arc.get("event_ids") or [])
        if not event_ids:
            continue
        # 取第一/最后 event 的 timestamp 作为 start/end
        tss = [e["timestamp"] for e in events if e["event_id"] in event_ids and e["timestamp"]]
        conn.execute(
            """INSERT INTO narrative_arcs(arc_id, title, summary, theme,
               start_at, end_at, scene_id, metadata_json, created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (arc_id, arc.get("title", ""), arc.get("summary", ""),
             arc.get("theme", ""), min(tss) if tss else None,
             max(tss) if tss else None, scene_id,
             json.dumps({"source": "llm"}), now),
        )
        for i, eid in enumerate(event_ids):
            conn.execute(
                "INSERT OR IGNORE INTO narrative_arc_events(arc_id, event_id, ordering) "
                "VALUES(?, ?, ?)",
                (arc_id, eid, i),
            )
        created.append({"arc_id": arc_id, "title": arc.get("title"),
                         "theme": arc.get("theme"), "event_count": len(event_ids)})
    conn.commit()
    conn.close()
    return {"arc_count": len(created), "arcs": created}


def list_arcs(db_path: Path, *, scene_id: str | None = None, limit: int = 20) -> list[dict]:
    conn = connect(db_path)
    if scene_id:
        rows = conn.execute(
            "SELECT arc_id, title, theme, summary, start_at, end_at "
            "FROM narrative_arcs WHERE scene_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (scene_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT arc_id, title, theme, summary, start_at, end_at "
            "FROM narrative_arcs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out = []
    for r in rows:
        events = conn.execute(
            "SELECT event_id FROM narrative_arc_events WHERE arc_id = ? ORDER BY ordering",
            (r[0],),
        ).fetchall()
        out.append({
            "arc_id": r[0], "title": r[1], "theme": r[2],
            "summary": r[3], "start_at": r[4], "end_at": r[5],
            "event_ids": [e[0] for e in events],
        })
    conn.close()
    return out
