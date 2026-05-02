"""Person activity view：聚合一个 person 的近期图谱活动为单份 profile。

用于 debug / skill 展示 / "这个人最近在做什么？" 类询问。

返回：
  - person: 基础字段 + persona/style/boundary_summary
  - facets: person_facets 全量
  - recent_events: 近 N 个事件
  - active_relations: 该 person 参与的所有 active relation（含对方 display_name）
  - memories: owner 包含此 person 的 active memory
  - scenes: 该 person 参与的所有 active scene
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from we_together.db.connection import connect


def build_person_activity(
    db_path: Path,
    person_id: str,
    *,
    event_limit: int = 20,
) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row

    person_row = conn.execute(
        """
        SELECT person_id, primary_name, status, persona_summary, style_summary,
               boundary_summary, work_summary, life_summary, confidence
        FROM persons WHERE person_id = ?
        """,
        (person_id,),
    ).fetchone()
    if person_row is None:
        conn.close()
        raise ValueError(f"Person not found: {person_id}")

    facets = [
        {
            "facet_type": r["facet_type"],
            "facet_key": r["facet_key"],
            "facet_value": (json.loads(r["facet_value_json"]).get("value")
                             if r["facet_value_json"] else None),
            "confidence": r["confidence"],
        }
        for r in conn.execute(
            """
            SELECT facet_type, facet_key, facet_value_json, confidence
            FROM person_facets WHERE person_id = ?
            ORDER BY facet_type, facet_key
            """,
            (person_id,),
        ).fetchall()
    ]

    recent_events = [
        {
            "event_id": r["event_id"],
            "event_type": r["event_type"],
            "timestamp": r["timestamp"],
            "summary": r["summary"],
        }
        for r in conn.execute(
            """
            SELECT e.event_id, e.event_type, e.timestamp, e.summary
            FROM events e
            JOIN event_participants ep ON ep.event_id = e.event_id
            WHERE ep.person_id = ?
            ORDER BY e.timestamp DESC
            LIMIT ?
            """,
            (person_id, event_limit),
        ).fetchall()
    ]

    active_relations = [
        {
            "relation_id": r["relation_id"],
            "core_type": r["core_type"],
            "custom_label": r["custom_label"],
            "summary": r["summary"],
            "strength": r["strength"],
            "other_person_ids": json.loads(r["participants_json"] or "[]"),
        }
        for r in conn.execute(
            """
            SELECT DISTINCT r.relation_id, r.core_type, r.custom_label, r.summary, r.strength,
                            (SELECT json_group_array(DISTINCT ep2.person_id) FROM event_participants ep2
                             JOIN event_targets et2 ON et2.event_id = ep2.event_id
                             WHERE et2.target_type = 'relation' AND et2.target_id = r.relation_id
                               AND ep2.person_id != ?) AS participants_json
            FROM relations r
            JOIN event_targets et ON et.target_type = 'relation' AND et.target_id = r.relation_id
            JOIN event_participants ep ON ep.event_id = et.event_id
            WHERE ep.person_id = ? AND r.status = 'active'
            """,
            (person_id, person_id),
        ).fetchall()
    ]

    memories = [
        {
            "memory_id": r["memory_id"],
            "memory_type": r["memory_type"],
            "summary": r["summary"],
            "relevance_score": r["relevance_score"],
        }
        for r in conn.execute(
            """
            SELECT DISTINCT m.memory_id, m.memory_type, m.summary, m.relevance_score
            FROM memories m
            JOIN memory_owners mo ON mo.memory_id = m.memory_id
            WHERE mo.owner_id = ? AND mo.owner_type = 'person' AND m.status = 'active'
            ORDER BY m.relevance_score DESC, m.created_at DESC
            LIMIT 20
            """,
            (person_id,),
        ).fetchall()
    ]

    scenes = [
        {
            "scene_id": r["scene_id"],
            "scene_type": r["scene_type"],
            "scene_summary": r["scene_summary"],
            "activation_state": r["activation_state"],
            "activation_score": r["activation_score"],
        }
        for r in conn.execute(
            """
            SELECT s.scene_id, s.scene_type, s.scene_summary,
                   sp.activation_state, sp.activation_score
            FROM scenes s
            JOIN scene_participants sp ON sp.scene_id = s.scene_id
            WHERE sp.person_id = ? AND s.status = 'active'
            """,
            (person_id,),
        ).fetchall()
    ]

    conn.close()

    return {
        "person": {
            "person_id": person_row["person_id"],
            "primary_name": person_row["primary_name"],
            "persona_summary": person_row["persona_summary"],
            "style_summary": person_row["style_summary"],
            "boundary_summary": person_row["boundary_summary"],
            "confidence": person_row["confidence"],
        },
        "facets": facets,
        "recent_events": recent_events,
        "active_relations": active_relations,
        "memories": memories,
        "scenes": scenes,
    }
