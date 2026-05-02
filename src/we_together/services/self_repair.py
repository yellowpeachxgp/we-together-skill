"""self_repair（Phase 45 GT-10/11）：把 integrity_audit 找到的异常转成 patch proposal。

policy:
- report_only：只返报告，不改图
- propose：返回 patch 列表（用户审）
- auto：执行"安全修复"（仅 dangling_memory_owners 删除 owner row + orphaned memory → status='cold'）
        破坏性修复（如 merge 撤销）永远不在 auto 模式
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from we_together.services.integrity_audit import full_audit


Policy = Literal["report_only", "propose", "auto"]


def _apply_safe_fixes(db_path: Path, report: dict) -> list[dict]:
    actions: list[dict] = []
    conn = sqlite3.connect(db_path)
    try:
        for item in report.get("dangling_memory_owners", []):
            conn.execute(
                "DELETE FROM memory_owners WHERE memory_id=? AND owner_id=?",
                (item["memory_id"], item["owner_id"]),
            )
            actions.append({
                "action": "delete_memory_owner",
                "memory_id": item["memory_id"], "owner_id": item["owner_id"],
            })
        for item in report.get("orphaned_memories", []):
            conn.execute(
                "UPDATE memories SET status='cold', updated_at=datetime('now') "
                "WHERE memory_id=?",
                (item["memory_id"],),
            )
            actions.append({
                "action": "mark_memory_cold",
                "memory_id": item["memory_id"],
            })
        conn.commit()
    finally:
        conn.close()
    return actions


def _propose_fixes(report: dict) -> list[dict]:
    proposals: list[dict] = []
    for item in report.get("dangling_memory_owners", []):
        proposals.append({
            "type": "delete_memory_owner",
            "memory_id": item["memory_id"],
            "owner_id": item["owner_id"],
            "rationale": "owner_id points to missing person",
            "severity": "low",
        })
    for item in report.get("orphaned_memories", []):
        proposals.append({
            "type": "mark_memory_cold",
            "memory_id": item["memory_id"],
            "rationale": "active memory with no owner",
            "severity": "medium",
        })
    for item in report.get("merged_without_target", []):
        proposals.append({
            "type": "unmerge_or_mark_inactive",
            "person_id": item["person_id"],
            "issue": item["issue"],
            "rationale": "merged without valid merged_into target",
            "severity": "high",
            "human_gate": True,
        })
    return proposals


def self_repair(db_path: Path, *, policy: Policy = "report_only") -> dict:
    report = full_audit(db_path)

    if policy == "report_only":
        return {"policy": policy, "report": report, "actions": [], "proposals": []}

    if policy == "propose":
        return {
            "policy": policy,
            "report": report,
            "actions": [],
            "proposals": _propose_fixes(report),
        }

    # auto
    actions = _apply_safe_fixes(db_path, report)
    proposals = _propose_fixes(report)
    # auto 只执行 safe fix；剩下（含 high severity）仍只返 proposal
    remaining = [p for p in proposals if p.get("severity") == "high"]
    return {
        "policy": policy,
        "report": report,
        "actions": actions,
        "proposals": remaining,
    }
