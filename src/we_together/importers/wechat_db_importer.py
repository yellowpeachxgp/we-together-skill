"""微信数据库 importer（明文 sqlite 版本）。

历史上微信 db 是加密 sqlcipher；本 importer 只支持已解密的明文 sqlite 文件。
加密路径留给外部工具（例如 ex-skill/tools/wechat_decryptor）处理。

最小 schema 假设:
  contact(wxid, nickname, remark)
  message(msg_id, wxid, content, createTime, is_send, room_id)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def import_wechat_db(db_file: Path, *, limit: int | None = 500) -> dict:
    if not db_file.exists():
        raise FileNotFoundError(f"WeChat db not found: {db_file}")
    conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    contacts = conn.execute("SELECT wxid, nickname, remark FROM contact").fetchall()
    identity_candidates = [
        {
            "display_name": c["remark"] or c["nickname"] or c["wxid"],
            "platform": "wechat",
            "external_id": c["wxid"],
            "confidence": 0.6,
            "source": "wechat_db",
        }
        for c in contacts
    ]

    q = """
        SELECT msg_id, wxid, content, createTime, is_send, room_id
        FROM message
        WHERE content IS NOT NULL AND content != ''
        ORDER BY createTime DESC
    """
    if limit:
        q += f" LIMIT {int(limit)}"
    msgs = conn.execute(q).fetchall()
    event_candidates = [
        {
            "summary": m["content"],
            "event_type": "dialogue_event",
            "timestamp": str(m["createTime"]),
            "sender_external_id": m["wxid"],
            "room_id": m["room_id"],
            "is_send": bool(m["is_send"]),
            "guid": m["msg_id"],
            "confidence": 0.65,
            "source": "wechat_db",
        }
        for m in msgs
    ]

    conn.close()
    return {
        "identity_candidates": identity_candidates,
        "event_candidates": event_candidates,
        "source": "wechat_db",
        "db_path": str(db_file),
    }
