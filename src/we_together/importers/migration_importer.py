"""通用 CSV importer (IO-1)：任意 CSV → candidate 层。

期望列（任选子集）:
  - person_name / name / display_name  → identity_candidates
  - content / text / summary / message → event_candidates.summary
  - timestamp / ts / time / date       → event_candidates.timestamp
  - sender / author / from / speaker   → event_candidates.sender_external_id
  - relation_type                       → relation_clues.core_type
  - person_a / person_b                 → relation_clues pair
"""
from __future__ import annotations

import csv
from pathlib import Path


NAME_FIELDS = ("person_name", "name", "display_name")
TEXT_FIELDS = ("content", "text", "summary", "message", "body")
TS_FIELDS = ("timestamp", "ts", "time", "date", "created_at")
SENDER_FIELDS = ("sender", "author", "from", "speaker")


def _pick(row: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        if k in row and row[k]:
            return row[k]
    return None


def import_csv(
    csv_path: Path, *, source_name: str | None = None,
) -> dict:
    if not csv_path.exists():
        raise FileNotFoundError(f"csv not found: {csv_path}")

    identities: dict[str, dict] = {}
    events: list[dict] = []
    relation_clues: list[dict] = []

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = _pick(row, NAME_FIELDS)
            if name and name not in identities:
                identities[name] = {
                    "display_name": name,
                    "platform": source_name or "csv",
                    "external_id": name,
                    "confidence": 0.55,
                    "source": "csv_importer",
                }
            text = _pick(row, TEXT_FIELDS)
            ts = _pick(row, TS_FIELDS)
            sender = _pick(row, SENDER_FIELDS) or name
            if sender and sender not in identities:
                identities[sender] = {
                    "display_name": sender, "platform": source_name or "csv",
                    "external_id": sender, "confidence": 0.55,
                    "source": "csv_importer",
                }
            if text:
                events.append({
                    "summary": text[:500],
                    "event_type": "csv_event",
                    "timestamp": ts,
                    "sender_external_id": sender,
                    "confidence": 0.55,
                    "source": "csv_importer",
                })
            # relation_clue 可选
            a = row.get("person_a"); b = row.get("person_b")
            if a and b:
                for n in (a, b):
                    if n not in identities:
                        identities[n] = {
                            "display_name": n, "platform": source_name or "csv",
                            "external_id": n, "confidence": 0.55,
                            "source": "csv_importer",
                        }
                relation_clues.append({
                    "a": a, "b": b,
                    "core_type": row.get("relation_type") or "mention",
                    "confidence": 0.5,
                    "source_row": reader.line_num,
                })

    return {
        "identity_candidates": list(identities.values()),
        "event_candidates": events,
        "relation_clues": relation_clues,
        "source": "csv_importer",
        "row_count": len(events),
    }


def import_notion_export(export_dir: Path) -> dict:
    """Notion markdown export：每个 .md 一个 page，文件名 = 标题。

    复用 obsidian_md_importer 的 wikilink 逻辑。
    """
    from we_together.importers.obsidian_md_importer import import_obsidian_vault
    result = import_obsidian_vault(export_dir)
    # 打标：source = notion_export
    for c in result["identity_candidates"]:
        c["source"] = "notion_export"
        c["platform"] = "notion"
    for e in result["event_candidates"]:
        e["source"] = "notion_export"
        e["event_type"] = "notion_page_event"
    result["source"] = "notion_export"
    return result


def import_signal_export(json_path: Path) -> dict:
    """Signal JSON export：{conversations: [{participants, messages: [{sender, text, timestamp}]}]}"""
    import json
    if not json_path.exists():
        raise FileNotFoundError(f"signal export not found: {json_path}")
    data = json.loads(json_path.read_text(encoding="utf-8"))

    identities: dict[str, dict] = {}
    events: list[dict] = []
    for conv in data.get("conversations", []):
        for p in conv.get("participants", []):
            if p and p not in identities:
                identities[p] = {
                    "display_name": p, "platform": "signal",
                    "external_id": p, "confidence": 0.6,
                    "source": "signal_export",
                }
        for msg in conv.get("messages", []):
            sender = msg.get("sender")
            if sender and sender not in identities:
                identities[sender] = {
                    "display_name": sender, "platform": "signal",
                    "external_id": sender, "confidence": 0.6,
                    "source": "signal_export",
                }
            events.append({
                "summary": msg.get("text", "")[:500],
                "event_type": "signal_message_event",
                "timestamp": msg.get("timestamp"),
                "sender_external_id": sender,
                "confidence": 0.6,
                "source": "signal_export",
            })
    return {
        "identity_candidates": list(identities.values()),
        "event_candidates": events,
        "source": "signal_export",
    }
