"""unmerge_gate_service：为 merged person 打开 operator-gated unmerge branch。"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


def _clamp_confidence(confidence: float) -> float:
    return max(0.0, min(1.0, confidence))


def _get_merged_target(db_path: Path, source_pid: str) -> str:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT status, metadata_json FROM persons WHERE person_id = ?",
            (source_pid,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        raise ValueError(f"person not found: {source_pid}")
    if row["status"] != "merged":
        raise ValueError(f"person {source_pid} is not in merged state")
    meta = json.loads(row["metadata_json"] or "{}")
    target_pid = meta.get("merged_into")
    if not target_pid:
        raise ValueError(f"person {source_pid} has no merged_into record")
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        target_row = conn.execute(
            "SELECT person_id, status FROM persons WHERE person_id = ?",
            (target_pid,),
        ).fetchone()
    finally:
        conn.close()
    if not target_row:
        raise ValueError(f"person {source_pid} merged_into target not found: {target_pid}")
    if target_row["status"] != "active":
        raise ValueError(f"person {source_pid} merged_into target is not active: {target_pid}")
    return target_pid


def open_unmerge_branch_for_merged_person(
    db_path: Path,
    *,
    source_pid: str,
    confidence: float = 0.8,
    reason: str,
    note: str | None = None,
    reviewer: str = "operator_gate",
) -> dict:
    confidence = _clamp_confidence(confidence)
    target_pid = _get_merged_target(db_path, source_pid)
    branch_id = f"branch_unmerge_{uuid.uuid4().hex[:12]}"
    keep_candidate_id = f"cand_keep_{uuid.uuid4().hex[:8]}"
    unmerge_candidate_id = f"cand_unmerge_{uuid.uuid4().hex[:8]}"

    keep_payload = {
        "proposal_type": "keep_merged",
        "requires_operator_gate": True,
        "source_person_id": source_pid,
        "target_person_id": target_pid,
        "note": note or "",
    }
    unmerge_payload = {
        "proposal_type": "unmerge_person",
        "requires_operator_gate": True,
        "source_person_id": source_pid,
        "target_person_id": target_pid,
        "note": note or "",
        "effect_patches": [
            {
                "target_type": "person",
                "target_id": source_pid,
                "operation": "unmerge_person",
                "payload": {
                    "source_person_id": source_pid,
                    "reviewer": reviewer,
                    "reason": reason,
                },
                "confidence": confidence,
                "reason": reason,
            }
        ],
    }

    patch = build_patch(
        source_event_id=f"evt_open_unmerge_{branch_id}",
        target_type="local_branch",
        target_id=branch_id,
        operation="create_local_branch",
        payload={
            "branch_id": branch_id,
            "scope_type": "person",
            "scope_id": source_pid,
            "status": "open",
            "reason": f"operator gate: {reason}",
            "created_from_event_id": f"evt_open_unmerge_{branch_id}",
            "branch_candidates": [
                {
                    "candidate_id": keep_candidate_id,
                    "label": "保留 merged 状态",
                    "payload_json": keep_payload,
                    "confidence": 1.0 - confidence,
                    "status": "open",
                },
                {
                    "candidate_id": unmerge_candidate_id,
                    "label": "执行 unmerge",
                    "payload_json": unmerge_payload,
                    "confidence": confidence,
                    "status": "open",
                },
            ],
        },
        confidence=confidence,
        reason="open operator-gated unmerge branch",
    )
    apply_patch_record(db_path=db_path, patch=patch)
    return {
        "branch_id": branch_id,
        "source_pid": source_pid,
        "target_pid": target_pid,
        "keep_candidate_id": keep_candidate_id,
        "unmerge_candidate_id": unmerge_candidate_id,
    }
