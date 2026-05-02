---
adr: 0057
title: Phase 55 — 差异化能力（working_memory + 派生重建）
status: Accepted
date: 2026-04-19
---

# ADR 0057: Phase 55 — 差异化能力双击

## 状态
Accepted — 2026-04-19

## 背景
v0.16 已具备长期记忆、神经网格、dream。但缺两项差异化：
1. **working memory**：当前 scene / tick 的高活性 context（短时、不落库）
2. **派生可重建性**：insight / activation_stats / narrative_arc 是否真能从底层 events 重建

这两条把 "we-together 与 Mem0/Letta 的差距" 拉到更清晰。

## 决策

### D1. services/working_memory
- `WorkingMemoryItem(content, kind, weight, source_refs, ttl_seconds)` + `to_dict`
- `WorkingMemoryBuffer(scene_id, capacity)`：
  - `add_note(content, kind, weight, source_refs, ttl_seconds)`
  - `snapshot()` 自动 prune 过期 + 超容量
- 全局 `get_buffer(scene_id)` per-scene registry
- **不落 db**；短时、轻量、进程重启即丢

### D2. services/derivation_rebuild
- `get_insight_sources(db, insight_id)` 读 `memory.metadata_json.source_memory_ids`
- `verify_insight_rebuildable(db, insight_id)`：≥ 60% source memory 还能找到 → True
- `rebuild_activation_edge_stats(db, since_days)` 从 activation_traces 重建
- `verify_narrative_arcs_rebuildable(db, arc_id)` 检查 narrative_arcs.source_event_refs_json
- `summary(db)` 整个图谱的可重建性体检

### D3. 不变式 #28 正式确立
**所有派生字段必须可从底层 events 重建；派生数据不得成为"唯一真相"。**

具体要求：
- insight memory 的 metadata.source_memory_ids 必填
- narrative_arcs 的 source_event_refs_json 必填
- persona_summary 派生自 person_facets（已有）
- activation_map / 激活统计派生自 activation_traces（已有）
- working_memory 是**短时派生**，不需要持久化可重建（进程重启即从 memories/events 重填）

### D4. 边界
- 不把 working_memory 强行塞进 `retrieval_package`（v1 schema 锁，#19）
- 由上层（chat_service / multi_agent_dialogue）按需调 `get_buffer(scene_id).snapshot()` 合并

## 不变式（新，v0.17 第 28 条）
**#28**：所有派生字段（persona_summary / narrative_arcs / activation_map / insight / working_memory）必须可从底层 events / memories 重建；派生数据不得成为"唯一真相"。

> 违反则一旦派生数据损坏，没有重算路径 → 图谱信任性崩塌。

## 版本锚点
- tests: +10 (test_phase_55_df.py)
- 文件: `services/working_memory.py` / `services/derivation_rebuild.py`

## 非目标（v0.18）
- narrative_v2：现有 narrative_service 已基本够用，v0.18 再深度升级
- memory_condenser 智能调度（自动按配额压缩）
- working_memory 持久化选项（某些场景希望跨 session）

## 拒绝的备选
- 把 working_memory 写 retrieval_cache：污染缓存表；短时不配持久化
- 派生强制自动校验：运行时开销大；显式 `verify_*` API 即可
