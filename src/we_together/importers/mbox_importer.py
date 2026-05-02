"""MBOX 批量邮件 importer。

Python 标准库 mailbox 足以解析 gmail takeout 级别的 .mbox。
输出符合 unified-importer-contract: IdentityCandidate + EventCandidate 列表。
"""
from __future__ import annotations

import mailbox
from pathlib import Path


def import_mbox(mbox_file: Path, *, limit: int | None = None) -> dict:
    if not mbox_file.exists():
        raise FileNotFoundError(f"MBOX not found: {mbox_file}")

    mbox = mailbox.mbox(str(mbox_file))
    identities: dict[str, dict] = {}
    events: list[dict] = []
    for i, msg in enumerate(mbox):
        if limit is not None and i >= limit:
            break
        sender = (msg.get("From") or "").strip()
        subject = (msg.get("Subject") or "").strip()
        date = (msg.get("Date") or "").strip()
        body = _extract_body(msg)
        if sender and sender not in identities:
            identities[sender] = {
                "display_name": sender,
                "platform": "email",
                "external_id": sender,
                "confidence": 0.7,
                "source": "mbox",
            }
        events.append({
            "summary": subject or body[:120],
            "event_type": "email_event",
            "timestamp": date,
            "sender_external_id": sender,
            "subject": subject,
            "body_preview": body[:500],
            "confidence": 0.7,
            "source": "mbox",
        })

    return {
        "identity_candidates": list(identities.values()),
        "event_candidates": events,
        "source": "mbox",
        "mbox_path": str(mbox_file),
    }


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    return ""
        return ""
    try:
        return (msg.get_payload(decode=True) or b"").decode("utf-8", errors="ignore")
    except Exception:
        return ""
