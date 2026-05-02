"""场景转换推荐服务。

给定当前 scene，基于图谱推荐可能的下一场景：
  - 同参与者 + 切换 scene_type（work → casual / casual → intimate）
  - 同参与者 + 加入共享 group 成员
  - 同关系链 + 新的 scene

这是 Phase 6 的增强，让 Skill 能"察觉可以切换场景"的信号。
返回候选列表（不自动创建 scene，只推荐）。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.db.connection import connect


SCENE_TYPE_TRANSITIONS: dict[str, list[str]] = {
    "work_discussion": ["casual_social", "private_chat"],
    "meeting": ["work_discussion", "casual_social"],
    "casual_social": ["private_chat", "intimate"],
    "private_chat": ["intimate", "casual_social"],
    "intimate": ["private_chat"],
    "group_chat": ["work_discussion", "casual_social"],
}


def suggest_next_scenes(db_path: Path, current_scene_id: str, limit: int = 3) -> list[dict]:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    scene = conn.execute(
        "SELECT scene_id, scene_type, group_id FROM scenes WHERE scene_id = ?",
        (current_scene_id,),
    ).fetchone()
    if scene is None:
        conn.close()
        raise ValueError(f"Scene not found: {current_scene_id}")

    participants = [
        row["person_id"]
        for row in conn.execute(
            "SELECT person_id FROM scene_participants WHERE scene_id = ?",
            (current_scene_id,),
        ).fetchall()
    ]

    next_types = SCENE_TYPE_TRANSITIONS.get(scene["scene_type"], ["casual_social"])

    suggestions: list[dict] = []
    # 1. 保留参与者 + 切换 scene_type
    for nt in next_types:
        suggestions.append({
            "kind": "same_participants_new_type",
            "scene_type": nt,
            "participant_person_ids": participants,
            "rationale": f"保留参与者, 切换到 {nt}",
        })

    # 2. 若有 group，扩展到 group 下一层：当前未出席但活跃的成员
    if scene["group_id"]:
        extra_members = [
            row["person_id"]
            for row in conn.execute(
                """
                SELECT person_id FROM group_members
                WHERE group_id = ? AND status = 'active' AND person_id NOT IN (%s)
                LIMIT 5
                """ % (",".join("?" * len(participants)) or "''"),
                (scene["group_id"], *participants),
            ).fetchall()
        ]
        if extra_members:
            suggestions.append({
                "kind": "expand_group",
                "scene_type": "group_chat",
                "participant_person_ids": participants + extra_members[:2],
                "rationale": f"扩展到 group {scene['group_id']} 的 {len(extra_members)} 名成员",
            })

    # 3. 借用共享关系对方：同参与者的 relation 参与者中未出席者
    if participants:
        rel_partners = [
            row["person_id"]
            for row in conn.execute(
                """
                SELECT DISTINCT ep.person_id FROM events e
                JOIN event_participants ep ON ep.event_id = e.event_id
                JOIN event_targets et ON et.event_id = e.event_id
                WHERE et.target_type = 'relation'
                AND ep.person_id NOT IN (%s)
                AND EXISTS (
                    SELECT 1 FROM event_participants ep2
                    WHERE ep2.event_id = e.event_id AND ep2.person_id IN (%s)
                )
                LIMIT 5
                """ % (
                    ",".join("?" * len(participants)),
                    ",".join("?" * len(participants)),
                ),
                (*participants, *participants),
            ).fetchall()
        ]
        if rel_partners:
            suggestions.append({
                "kind": "bring_relation_partner",
                "scene_type": "casual_social",
                "participant_person_ids": participants + rel_partners[:1],
                "rationale": f"加入共享 relation 的 {rel_partners[0]}",
            })

    conn.close()
    return suggestions[:limit]
