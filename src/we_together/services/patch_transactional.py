"""事务化 patch 批处理：用单一 conn + 单个事务把一批 patch 当原子组。

**注意当前实现**：只写 patches 表记录（影子 insert），不触发 apply_patch_record 的
所有副作用（实体本体变更、memory_owners 手动写、cache invalidation 等）。

真正的"apply_patch_record 接受外部 conn"重构留给 Phase 22（HD-8 续）。
当前 ADR 0009 D-EXT / ADR 0014 的一致性保证：patches 表本身的原子性。

用法：
  - 你只需要"一次性记录一批 patch 到 patches 表"：用本函数
  - 你需要"所有 patch 真正生效（含副作用）且失败回滚"：patch_transactional 暂不支持，
    改用 apply_patches_bulk（顺序半事务）
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from we_together.errors import PatchError


def apply_patches_transactional(
    db_path: Path, patches: list[dict],
) -> dict:
    """整组事务：任一 patch 失败 → ROLLBACK 全部。

    注意：本函数跳过 apply_patch_record 的事件传播/缓存失效等副作用，
    只做 patches 表的插入记录 + 基本字段更新。用于测试级别的 bulk insert。
    完整语义保留在 patch_applier.apply_patch_record 单条版本。
    """
    if not patches:
        return {"applied_count": 0, "failed_count": 0, "rolled_back": False}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    applied: list[str] = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        for p in patches:
            pid = p.get("patch_id") or f"tx_{len(applied)}"
            conn.execute(
                """INSERT INTO patches(patch_id, source_event_id, target_type, target_id,
                   operation, payload_json, confidence, reason, status, applied_at,
                   created_at) VALUES(?,?,?,?,?,?,?,?,'applied',datetime('now'),
                   datetime('now'))""",
                (pid, p.get("source_event_id"), p.get("target_type"),
                 p.get("target_id"), p.get("operation"),
                 __import__("json").dumps(p.get("payload", {}), ensure_ascii=False),
                 p.get("confidence"), p.get("reason")),
            )
            applied.append(pid)
        conn.commit()
        conn.close()
        return {"applied_count": len(applied), "failed_count": 0,
                "rolled_back": False, "applied_ids": applied}
    except Exception as exc:
        conn.rollback()
        conn.close()
        raise PatchError(f"transactional bulk failed: {exc}") from exc
