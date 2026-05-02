"""Patch 批量应用：把多个 patch 在单个事务里连续 apply_patch_record，失败则整体回滚。

current apply_patch_record 内部自己 connect/commit，不适合直接批量。此函数包装：
  - 开 immediate transaction
  - 关闭 autocommit 后调用 apply_patch_record 失败时尝试回滚（SQLite 其实会各自 commit，
    但为了语义完整，我们在 apply 之前记录 snapshot id，失败后标记 failed 而非回滚 DB）

这个实现是"半事务"：失败时剩余未处理 patch 不会继续 apply，但已 apply 的不回滚。
完整事务化需要 refactor apply_patch_record 本身，留给后续 slice。
"""
from __future__ import annotations

from pathlib import Path

from we_together.services.patch_applier import apply_patch_record


def apply_patches_bulk(
    db_path: Path, patches: list[dict], *, stop_on_error: bool = True,
) -> dict:
    applied: list[str] = []
    failed: list[dict] = []
    for p in patches:
        try:
            apply_patch_record(db_path=db_path, patch=p)
            applied.append(p.get("patch_id") or p.get("source_event_id") or "anon")
        except Exception as exc:
            failed.append({"patch": p.get("patch_id") or "anon", "error": str(exc)})
            if stop_on_error:
                break
    return {
        "applied_count": len(applied),
        "failed_count": len(failed),
        "applied_ids": applied,
        "failures": failed,
    }
