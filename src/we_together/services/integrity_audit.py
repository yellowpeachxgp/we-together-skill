"""integrity_audit（Phase 45 GT-6/7/8/9）：图谱异常巡检。

不变动任何数据，只读返回报告。修复由 self_repair 配合不变式 #18（gate）触发。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path


def check_dangling_memory_owners(db_path: Path) -> list[dict]:
    """memory_owners.owner_id 指向不存在的 person。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT mo.memory_id, mo.owner_id FROM memory_owners mo
               WHERE mo.owner_type='person'
                 AND NOT EXISTS (
                   SELECT 1 FROM persons p WHERE p.person_id=mo.owner_id
                 )"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def check_orphaned_memories(db_path: Path) -> list[dict]:
    """active memory 但无 owner。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT m.memory_id, m.summary FROM memories m
               WHERE m.status='active'
                 AND NOT EXISTS (
                   SELECT 1 FROM memory_owners mo WHERE mo.memory_id=m.memory_id
                 )"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def check_low_confidence_memories(db_path: Path, *, threshold: float = 0.05) -> list[dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT memory_id, confidence FROM memories
               WHERE status='active' AND confidence IS NOT NULL AND confidence < ?""",
            (threshold,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def check_relation_cycles(db_path: Path) -> list[dict]:
    """简化：找自环 relation（a 连到自己）。真 cycle 检测留更大版本。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """SELECT r.relation_id, e1.to_id AS person_id
               FROM relations r
               JOIN entity_links e1 ON e1.from_type='relation'
                 AND e1.from_id=r.relation_id AND e1.relation_type='participant'
               WHERE r.status='active'
                 AND (
                   SELECT COUNT(DISTINCT e2.to_id) FROM entity_links e2
                   WHERE e2.from_type='relation' AND e2.from_id=r.relation_id
                     AND e2.relation_type='participant'
                 ) = 1
               GROUP BY r.relation_id"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def check_merged_without_target(db_path: Path) -> list[dict]:
    """status=merged 但 metadata_json.merged_into 不存在或目标 person 没找到。"""
    import json
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT person_id, metadata_json FROM persons WHERE status='merged'"
        ).fetchall()
        out: list[dict] = []
        for r in rows:
            meta = json.loads(r["metadata_json"] or "{}")
            target = meta.get("merged_into")
            if not target:
                out.append({"person_id": r["person_id"], "issue": "no_merged_into"})
                continue
            t_row = conn.execute(
                "SELECT 1 FROM persons WHERE person_id=?", (target,),
            ).fetchone()
            if not t_row:
                out.append({"person_id": r["person_id"], "issue": "missing_target",
                              "target": target})
        return out
    finally:
        conn.close()


def full_audit(db_path: Path) -> dict:
    dangling = check_dangling_memory_owners(db_path)
    orphans = check_orphaned_memories(db_path)
    low = check_low_confidence_memories(db_path)
    cycles = check_relation_cycles(db_path)
    bad_merged = check_merged_without_target(db_path)
    total = len(dangling) + len(orphans) + len(low) + len(cycles) + len(bad_merged)
    return {
        "dangling_memory_owners": dangling,
        "orphaned_memories": orphans,
        "low_confidence_memories": low,
        "relation_cycles": cycles,
        "merged_without_target": bad_merged,
        "total_issues": total,
        "healthy": total == 0,
    }
