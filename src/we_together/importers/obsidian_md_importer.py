"""Obsidian md importer：读 vault 目录下的 .md 文件，抽取 [[wikilinks]] 作为 person。

Vault 约定：
  - 每个 .md 文件名即 person 的 primary_name（去掉 .md）
  - 文件内容 [[Alice]] 形式的 wikilink 表示引用其他 person
  - "---" YAML frontmatter 可含 `type: person|memory|scene|skip`，默认 person
  - Body 作为 narration 文本，触发 candidate 抽取

输出 identity_candidates + event_candidates + relation_clues（基于共现）。
"""
from __future__ import annotations

import re
from pathlib import Path

WIKILINK_RE = re.compile(r"\[\[([^\[\]]+?)\]\]")


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta_block = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta: dict = {}
    for line in meta_block.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, body


def import_obsidian_vault(vault_dir: Path) -> dict:
    if not vault_dir.exists() or not vault_dir.is_dir():
        raise FileNotFoundError(f"vault not found: {vault_dir}")

    identity: dict[str, dict] = {}
    events: list[dict] = []
    relation_clues: list[dict] = []

    for md in sorted(vault_dir.glob("**/*.md")):
        raw = md.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        if meta.get("type") == "skip":
            continue
        name = md.stem
        identity.setdefault(name, {
            "display_name": name,
            "platform": "obsidian",
            "external_id": str(md.relative_to(vault_dir)),
            "confidence": 0.6,
            "source": "obsidian_vault",
        })
        events.append({
            "summary": body[:200] or f"note: {name}",
            "event_type": "obsidian_note_event",
            "timestamp": None,
            "sender_external_id": name,
            "confidence": 0.55,
            "source": "obsidian_vault",
            "note_path": str(md.relative_to(vault_dir)),
        })
        mentions = set(WIKILINK_RE.findall(body))
        for other in mentions:
            if other == name:
                continue
            identity.setdefault(other, {
                "display_name": other,
                "platform": "obsidian",
                "external_id": other,
                "confidence": 0.5,
                "source": "obsidian_vault",
            })
            relation_clues.append({
                "a": name, "b": other, "core_type": "mention",
                "confidence": 0.4, "source_note": str(md.relative_to(vault_dir)),
            })

    return {
        "identity_candidates": list(identity.values()),
        "event_candidates": events,
        "relation_clues": relation_clues,
        "source": "obsidian_vault",
        "vault_dir": str(vault_dir),
    }
