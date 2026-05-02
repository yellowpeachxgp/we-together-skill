---
adr: 0054
title: Phase 52 — AI Agent 元能力（自主 + 梦 + 学习）
status: Accepted
date: 2026-04-19
---

# ADR 0054: Phase 52 — AI Agent 元能力

## 状态
Accepted — 2026-04-19

## 背景
此前所有 agent 行为都被**外部**触发（tick / orchestrator / 用户输入）。vision "**神经单元网格式激活传播**"和"**数字赛博生态圈**"暗示 agent 需要**内在驱动力**——它应该自己知道什么时候想联系谁、什么时候该休息。
同时：图谱需要**睡眠期**——离线时段做压缩、关联发现、学习。

## 决策

### D1. Migration 0021_agent_drives
- `agent_drives(drive_id, person_id, drive_type, intensity, source_memory_ids, source_event_ids, status, ...)`
- `autonomous_actions(action_id, person_id, action_type, triggered_by_drive_id/memory/trace, output_event_id, rationale)`
- 追加式；`drive.status='satisfied'` 后不 update，新一轮生成新 drive

### D2. autonomous_agent 服务
- `DRIVE_RULES`：5 类 drive（connection / curiosity / resolve / obligation / rest）的关键词映射
- `compute_drives(db, person_id, lookback_days)`：扫 memory + event，启发式检测 drive
- `persist_drives` 落库
- `decide_action(drives, threshold)` → `Intent(action_type, reason, drive_id)`
- `record_autonomous_action` **强制校验**必须有 drive/memory/trace 至少一个来源（不变式 #27）

### D3. dream_cycle 服务
- `run_dream_cycle(db, min_cluster_size, lookback_days, archive_low_relevance)`
- 三步：
  1. 调用 `forgetting_service.archive_stale_memories` 压缩低相关
  2. `generate_insights` 检测 memory 簇 → 生成 `InsightSeed`
  3. `persist_insight` 写入 `memories(memory_type='insight')`，metadata 保留 source_memory_ids
- **不真调 LLM**（v0.17 MVP）；真 LLM 留给 simulate_year 真跑

### D4. Insight 类型
新 memory_type `insight`：
- 由 dream_cycle 产生
- `metadata.source='dream_cycle'`
- `metadata.source_memory_ids=[...]`（为 Phase 55 不变式 #28"派生可重建"铺路）

### D5. 安全边界
- `record_autonomous_action` 必须有来源（ValueError）
- Drive 强度 < threshold 时 `decide_action` 返 None
- LLM 预算控制交由上层（tick 内跑 dream 有 budget 参数）

## 不变式（新，v0.17 第 27 条）
**#27**：Agent 自主行为必须可解释——每次 `autonomous_actions` 行必须能追溯到 drive / memory / trace 至少一个来源。
> 违反则 agent 自发行为变黑盒，无法审计 / 调试 / 拒绝。

## 版本锚点
- tests: +11 (test_phase_52_ag.py)
- 文件: migration 0021 / `services/autonomous_agent.py` / `services/dream_cycle.py` / `scripts/dream_cycle.py`
- schema: 0020 → 0021

## 非目标（v0.18）
- LLM-based drive 检测（当前关键词启发）
- agent learning 真更新 persona_facets（与 persona_drift_service 深度整合）
- 跨 agent 协作（task decomposition）
- drive satisfaction 自动检测（当前只标 active，满足需显式 set）
- "情感生态"：群体情绪 state

## 拒绝的备选
- 让 `autonomous_agent` 直接 `run_turn`：违反 SkillRuntime v1 单向数据流；上层 orchestrator 更合适
- dream_cycle 真调 LLM 做归纳：成本失控；留作可选真跑
- Drive 存储在 person_facets：drive 是**短时动态**，facet 是**长期稳定**；独立表更清晰
