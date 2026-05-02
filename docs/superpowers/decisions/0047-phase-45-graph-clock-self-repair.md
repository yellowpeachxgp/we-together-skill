---
adr: 0047
title: Phase 45 — 图谱时间 + 自修复
status: Accepted
date: 2026-04-19
---

# ADR 0047: Phase 45 — 图谱时间 + 自修复

## 状态
Accepted — 2026-04-19

## 背景
vision "可持续演化"要求系统能在**长时间**下自演化。v0.15 前 tick 用真实 `datetime.now(UTC)`，无法加速模拟一年。同时图谱长时间运行必然出现 dangling refs / orphaned memory / 冲突，却没有巡检与自修复机制。这两件事一起做。

## 决策

### D1. migration 0017_graph_clock
- `graph_clock`：单行表，`simulated_now` / `speed_factor` / `frozen`
- `graph_clock_history`：追加式操作日志（set/advance/freeze/clear）
- bootstrap 时自动插入默认行（simulated_now=NULL 表示使用真时间）

### D2. services/graph_clock
- `now(db_path)`：优先模拟时间；不存在时回落 `datetime.now(UTC)`
- `set_time / advance / freeze / unfreeze / clear`
- **fallback 兼容**：db_path=None 或表不存在时直接返回真时间——保证现有代码不破
- **不强制迁移**：时间敏感服务按需改读 `graph_clock.now()`；未改的继续工作

### D3. services/integrity_audit
- `check_dangling_memory_owners` memory_owners 指向不存在 person
- `check_orphaned_memories` 无 owner 的 active memory
- `check_low_confidence_memories` confidence < 0.05
- `check_relation_cycles` 自环 relation（真 cycle 检测留 v0.17）
- `check_merged_without_target` status='merged' 但 metadata_json.merged_into 无效
- `full_audit()` 聚合报告 + `healthy` 标志

### D4. services/self_repair
- `policy ∈ {"report_only", "propose", "auto"}`
- `report_only`：只看
- `propose`：生成 patch proposal（带 severity + rationale；`human_gate` 标记高风险）
- `auto`：执行 **safe fix**（仅 `delete_memory_owner` dangling 行 + `mark_memory_cold` orphan memory）；破坏性修复（如 unmerge）**永远不在 auto 模式**
- 遵守不变式 #18（不自动改核心实体）+ #22（所有修复可回滚）

### D5. scripts/fix_graph.py + simulate_year.py
- `fix_graph --policy auto|propose|report_only`
- `simulate_year --days 365 --budget 50`：每天 advance_clock + 一次 tick，结束跑 integrity_audit

## 不变式（新，v0.16 第 24 条）
**#24**：时间敏感服务必须读 `graph_clock.now()` 优先，`datetime.now()` 仅限核心内核与无 db 上下文场景。
> 违反则加速模拟失效，一年模拟仍走真时间。

## 版本锚点
- tests: +15 (test_phase_45_gt.py)
- 文件: migration 0017 / `services/graph_clock.py` / `services/integrity_audit.py` / `services/self_repair.py` / `scripts/fix_graph.py` / `scripts/simulate_year.py`
- **向后兼容**：fallback 机制让现有代码不受影响；新旧测试全绿

## 非目标（v0.17）
- 现有 30+ 文件里 `datetime.now()` 的全面迁移（现在是**opt-in**）
- 真 cycle 检测（DFS、tarjan）
- self_repair 写 patch 到 patches 表（当前只返 proposal）
- auto policy 扩展到更多 severity 级别

## 拒绝的备选
- 强制替换所有 `datetime.now(UTC)`：破坏 30+ 文件测试
- 硬编单价的 cost / 时间关联：留给宿主层
- self_repair 自动 unmerge：违反不变式 #18
