---
adr: 0043
title: Phase 41 — 遗忘 / 压缩 / 拆分（图谱瘦身闭环）
status: Accepted
date: 2026-04-19
---

# ADR 0043: Phase 41 — 遗忘 / 压缩 / 拆分

## 状态
Accepted — 2026-04-19

## 背景
`product-mandate` 强调"可持续演化"，但持续演化 **必须有遗忘/压缩机制抗衡**，否则图谱无限膨胀。同时 vision 强调"默认可逆"——`merge_entities` 存在，但**没有对称的 unmerge**。这是 A 支柱"严格工程化"的拼图缺口。

## 决策

### D1. forgetting_service
- `ForgetParams(min_idle_days, max_relevance, limit, dry_run)`
- `archive_stale_memories` → status='cold'（**不物理删**，保留回溯）
- `_forget_score(days_idle, relevance)` Ebbinghaus-like 遗忘曲线
- `reactivate_memory(memory_id)` 对称撤销（#22）
- `condense_cluster_candidates` 识别 N 条 idle memory 同 owner 的候选（供 condenser 使用）
- `slimming_report()` 输出 active/cold/archived 占比

### D2. entity_unmerge_service
- `unmerge_person(source_pid, reviewer, reason)`：
  - 把 `status='merged'` + `metadata_json.merged_into` 的 person 置回 active
  - 在 `metadata_json.unmerge_history` 累计审计记录
  - 写 `events` 表 `event_type='unmerge_event'` 留痕
  - **不自动迁回** 已迁移的 identity_links / memory_owners（风险太高）；返回 `reviewed_required` 清单供人工审
- `list_merged_candidates()` 列出所有可 unmerge 的 person
- `derive_unmerge_candidates_from_contradictions()` 只产 candidate，不动图（#18 + #22）

### D3. 设计边界
- **不物理删除 memory**：status 流转 active → cold → archived（archived 留 v0.16）
- **不自动 unmerge**：contradiction_detector 可建议，但必须人工 gate（#18）
- **不自动迁回关系**：unmerge 只恢复 person status，关系迁回靠人工
- **遗忘曲线公开可测**：`_forget_score` 暴露让业务层调参

## 不变式（新，v0.15.0 第 22 条）
**#22**：图谱写入必须有对称的"撤销"路径。
- merge ↔ unmerge_person
- archive (status='cold') ↔ reactivate_memory
- create_memory ↔ mark_inactive
- record_dialogue ↔ rollback_to_snapshot
- 新增结构性写操作必须同时提供撤销方法，或在 ADR 里说明"为什么不需要撤销"

## 版本锚点
- tests: +10 (test_phase_41_fo.py)
- 文件: `services/forgetting_service.py` / `services/entity_unmerge_service.py`
- 不新增 migration（复用 memories.status / persons.status）

## 拒绝的备选
- 物理 DELETE memory：违反"事件优先 + 默认可逆"
- unmerge 自动迁回关系：迁移时已有 UPDATE OR IGNORE 冲突，回迁必产生歧义；交人工
- 新建 `forgotten_memories` 表：status 流转够用，独立表是过度设计
- forgetting 走 patch：forgetting 是图谱内部生命周期，不是外部事件驱动

## 留给 v0.16
- tick 内自动触发 `archive_stale_memories`（dry_run → 预算内真 archive）
- memory_condenser 真被 condense_cluster_candidates 驱动
- archive → archived （永久冷存）的迁移
- unmerge 的"智能迁回"proposals（以供审阅）
