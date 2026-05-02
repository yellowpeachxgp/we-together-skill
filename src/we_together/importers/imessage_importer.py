"""iMessage 本地 chat.db importer。

依赖 sqlite3 只读访问 macOS 的 ~/Library/Messages/chat.db。为了可测，本函数只接收
任意指向兼容 schema 的 sqlite 文件（测试会构造 fixture）。

最小 schema 假设（兼容 macOS chat.db 的核心子集）：
  message(ROWID, guid, text, handle_id, date, is_from_me)
  handle(ROWID, id, service)  -- id 通常是电话号码或 Apple ID
  chat(ROWID, guid, display_name)
  chat_message_join(chat_id, message_id)

输出: list[dict] candidates, 符合 unified-importer-contract (IdentityCandidate /
EventCandidate)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def import_imessage_db(chat_db: Path, *, limit: int | None = 200) -> dict:
    if not chat_db.exists():
        raise FileNotFoundError(f"iMessage db not found: {chat_db}")

    conn = sqlite3.connect(f"file:{chat_db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    # 参与者
    handles = conn.execute(
        "SELECT ROWID, id, service FROM handle"
    ).fetchall()
    identity_candidates = [
        {
            "display_name": h["id"],
            "platform": h["service"] or "imessage",
            "external_id": h["id"],
            "confidence": 0.6,
            "source": "imessage_db",
        }
        for h in handles
    ]

    # 消息作为 event_candidates
    q = """
        SELECT m.ROWID, m.guid, m.text, m.handle_id, m.date, m.is_from_me,
               h.id AS handle_identifier
        FROM message m
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        WHERE m.text IS NOT NULL AND m.text != ''
        ORDER BY m.date DESC
    """
    if limit:
        q += f" LIMIT {int(limit)}"
    msgs = conn.execute(q).fetchall()
    event_candidates = [
        {
            "summary": m["text"],
            "event_type": "dialogue_event",
            "timestamp": str(m["date"]),
            "sender_external_id": m["handle_identifier"],
            "is_from_me": bool(m["is_from_me"]),
            "guid": m["guid"],
            "confidence": 0.65,
            "source": "imessage_db",
        }
        for m in msgs
    ]

    conn.close()
    return {
        "identity_candidates": identity_candidates,
        "event_candidates": event_candidates,
        "source": "imessage_db",
        "db_path": str(chat_db),
    }
