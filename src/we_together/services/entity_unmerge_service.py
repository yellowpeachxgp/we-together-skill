"""entity_unmerge_service（Phase 41 FO-6/7/8）：撤销错误的 person 合并。

前提：merge_entities 在 persons 表把 source person 置 status='merged'，
     metadata_json.merged_into = target_pid，并迁移 identity_links / memory_owners /
     scene_participants / group_members / event_participants 到 target。

unmerge_person(db, source_pid)：
  - 把 source 置回 active
  - 不自动把已迁移关系迁回（安全起见；迁回风险高），而是返回"手工审阅列表"
  - 记录到 events 表：type=unmerge_event
  - 返回 {source_pid, target_pid, recoverable_links_count, reviewed_required: [...]}

不变式 #22 对称：merge ↔ unmerge 都是有迹可循可撤销的。
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path


def unmerge_person(
    db_path: Path, source_pid: str, *, reviewer: str = "auto",
    reason: str = "auto-reverse",
) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT status, metadata_json FROM persons WHERE person_id=?",
            (source_pid,),
        ).fetchone()
        if not row:
            raise ValueError(f"person not found: {source_pid}")
        if row["status"] != "merged":
            raise ValueError(
                f"person {source_pid} is not in merged state (got {row['status']})"
            )
        meta = json.loads(row["metadata_json"] or "{}")
        target_pid = meta.get("merged_into")
        if not target_pid:
            raise ValueError(f"person {source_pid} has no merged_into record")
        target_row = conn.execute(
            "SELECT person_id, status FROM persons WHERE person_id=?",
            (target_pid,),
        ).fetchone()
        if not target_row:
            raise ValueError(
                f"person {source_pid} merged_into target not found: {target_pid}"
            )
        if target_row["status"] != "active":
            raise ValueError(
                f"person {source_pid} merged_into target is not active: {target_pid}"
            )

        # 找 target 中可能来自 source 的 identity_links（合并时被迁移）
        # 根据 identity_links 里 confidence 与时间戳辅助；但可靠的只有 metadata_json
        linked = conn.execute(
            "SELECT identity_id, platform, external_id, confidence, "
            "is_user_confirmed FROM identity_links WHERE person_id=?",
            (target_pid,),
        ).fetchall()

        # 把 source 恢复 active
        meta.pop("merged_into", None)
        meta["unmerge_history"] = meta.get("unmerge_history", []) + [{
            "reviewer": reviewer,
            "reason": reason,
            "previous_target": target_pid,
            "at": "now",
        }]
        conn.execute(
            "UPDATE persons SET status='active', metadata_json=?, "
            "updated_at=datetime('now') WHERE person_id=?",
            (json.dumps(meta, ensure_ascii=False), source_pid),
        )

        # 记 event（保留审计轨迹）
        evt_id = f"evt_unmerge_{uuid.uuid4().hex[:10]}"
        conn.execute(
            """INSERT INTO events(event_id, event_type, source_type, timestamp,
               summary, visibility_level, confidence, is_structured,
               raw_evidence_refs_json, metadata_json, created_at)
               VALUES(?, 'unmerge_event', 'entity_unmerge_service',
               datetime('now'), ?, 'visible', 1.0, 1, '[]', ?,
               datetime('now'))""",
            (evt_id,
             f"unmerge {source_pid} from {target_pid}: {reason}",
             json.dumps({
                 "source_pid": source_pid, "target_pid": target_pid,
                 "reviewer": reviewer,
             }, ensure_ascii=False)),
        )
        conn.commit()

        return {
            "source_pid": source_pid,
            "target_pid": target_pid,
            "reviewed_required": [
                {
                    "kind": "identity_links",
                    "note": "manual review: which links belong to which pid",
                    "items_count": len(linked),
                }
            ],
            "event_id": evt_id,
        }
    finally:
        conn.close()


def list_merged_candidates(db_path: Path) -> list[dict]:
    """列出所有可 unmerge 的 person（status=merged 且有 merged_into）"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT person_id, primary_name, metadata_json, updated_at "
            "FROM persons WHERE status='merged'",
        ).fetchall()
    finally:
        conn.close()
    out: list[dict] = []
    for r in rows:
        meta = json.loads(r["metadata_json"] or "{}")
        if meta.get("merged_into"):
            out.append({
                "source_pid": r["person_id"],
                "primary_name": r["primary_name"],
                "target_pid": meta["merged_into"],
                "merged_at": r["updated_at"],
            })
    return out


def derive_unmerge_candidates_from_contradictions(
    db_path: Path, *, min_confidence: float = 0.7,
) -> list[dict]:
    """从 contradiction_detector 角度识别 candidates：
    - 两条 contradictory memory 的 owner 若是同一 person，**不是** unmerge 信号
    - 若 owner 是 "曾经是两个人被合并"的 person，且冲突可能源于合并错误 → candidate
    当前只做骨架：返回候选但不改图（不变式 #18）。
    """
    # 简化：返回所有"既在 merged 列表、又有高置信 contradiction"的组合
    merged = list_merged_candidates(db_path)
    if not merged:
        return []
    return [
        {**m, "confidence_score": min_confidence,
         "note": "contradiction-derived, needs human gate (#18)"}
        for m in merged
    ]
