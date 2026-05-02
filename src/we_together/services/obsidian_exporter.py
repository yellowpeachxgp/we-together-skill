"""Obsidian 反向 exporter：从图谱 person/memory 生成 vault md 文件。"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def export_to_obsidian_vault(db_path: Path, vault_dir: Path) -> dict:
    vault_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    persons = conn.execute(
        "SELECT person_id, primary_name, persona_summary, style_summary "
        "FROM persons WHERE status='active'"
    ).fetchall()
    exported: list[str] = []
    for p in persons:
        fname = f"{p['primary_name']}.md"
        content = f"""---
type: person
person_id: {p['person_id']}
---

# {p['primary_name']}

**Persona**: {p['persona_summary'] or '(未知)'}

**Style**: {p['style_summary'] or '(未知)'}

## 关联记忆
"""
        memories = conn.execute(
            """SELECT m.summary FROM memories m
               JOIN memory_owners mo ON mo.memory_id = m.memory_id
               WHERE mo.owner_id = ? AND m.status = 'active'
               LIMIT 10""",
            (p["person_id"],),
        ).fetchall()
        for m in memories:
            content += f"- {m['summary']}\n"

        (vault_dir / fname).write_text(content, encoding="utf-8")
        exported.append(fname)

    conn.close()
    return {"exported_count": len(exported), "files": exported,
            "vault_dir": str(vault_dir)}
