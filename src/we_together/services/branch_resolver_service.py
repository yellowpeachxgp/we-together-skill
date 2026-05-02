"""局部分支自动解决器。

当某个 open 的 local_branch 中存在置信度显著高的 candidate（绝对值 ≥ threshold 且
与次优 candidate 的差 ≥ margin）时，自动生成 resolve_local_branch patch 选中它。

保留"人类可覆盖"：auto resolve 的 reason 字段会标注 'auto:...'，便于审计和撤销。
显式 operator-gated branch 不参与 auto resolve。
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from we_together.db.connection import connect
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


def _is_operator_gated_branch(branch_reason: str | None, candidates: list[sqlite3.Row]) -> bool:
    if (branch_reason or "").startswith("operator gate:"):
        return True

    for cand in candidates:
        payload_json = cand["payload_json"]
        if not payload_json:
            continue
        payload = json.loads(payload_json)
        if payload.get("requires_operator_gate"):
            return True
    return False


def auto_resolve_branches(
    db_path: Path,
    *,
    threshold: float = 0.8,
    margin: float = 0.2,
    source_event_id: str | None = None,
) -> dict:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    branches = conn.execute(
        """
        SELECT branch_id, scope_type, scope_id, reason
        FROM local_branches
        WHERE status = 'open'
        """
    ).fetchall()

    resolved: list[dict] = []
    for br in branches:
        cands = conn.execute(
            """
            SELECT candidate_id, confidence, payload_json
            FROM branch_candidates
            WHERE branch_id = ? AND status = 'open'
            ORDER BY confidence DESC
            """,
            (br["branch_id"],),
        ).fetchall()
        if not cands:
            continue
        if _is_operator_gated_branch(br["reason"], cands):
            continue

        top_conf = cands[0]["confidence"] or 0.0
        second_conf = cands[1]["confidence"] if len(cands) > 1 else 0.0
        if top_conf < threshold:
            continue
        if (top_conf - (second_conf or 0.0)) < margin:
            continue

        resolved.append({
            "branch_id": br["branch_id"],
            "selected_candidate_id": cands[0]["candidate_id"],
            "top_conf": top_conf,
            "second_conf": second_conf,
        })
    conn.close()

    for item in resolved:
        patch = build_patch(
            source_event_id=source_event_id or f"auto_resolve_{item['branch_id']}",
            target_type="local_branch",
            target_id=item["branch_id"],
            operation="resolve_local_branch",
            payload={
                "branch_id": item["branch_id"],
                "status": "resolved",
                "reason": (
                    f"auto: top={item['top_conf']:.2f}, "
                    f"second={item['second_conf'] or 0:.2f}"
                ),
                "selected_candidate_id": item["selected_candidate_id"],
            },
            confidence=item["top_conf"],
            reason="branch auto-resolved",
        )
        apply_patch_record(db_path=db_path, patch=patch)

    return {"resolved_count": len(resolved), "details": resolved}
