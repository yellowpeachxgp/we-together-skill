# ADR 0012: Phase 15 — 时间维度（Timeline）

## 状态

Accepted — 2026-04-18

## 背景

图谱当前是"当下切片 + 点状 snapshot"。从社会视角看，时间本身应是第一类公民——persona 如何迁移、关系如何起落、事件如何回响、memory 如何在周年再浮现。

## 决策

### D1. persona_history 作为独立 append-only 表

migration 0009 新增 `persona_history(history_id, person_id, persona/style/boundary_summary, valid_from, valid_to, source_reason, confidence)`。valid_to=NULL 表示当前有效。`services/persona_history_service.record_persona_change` 插入新行并 close 前一条的 valid_to。`query_as_of(as_of_iso)` 按时间窗查询。

### D2. persona_drift 自动写 history

`persona_drift_service.drift_personas` 在每次 `update_entity` patch 落地后，额外调用 `record_persona_change`。历史保留零散本体上看不到的演变细节。

### D3. relation_history 基于 patches 聚合（不新建表）

`services/relation_history_service` 直接扫 `patches` 表（`target_type='relation' AND json_extract(payload_json,'$.strength') IS NOT NULL`），按 day/week/month bucket 聚合，避免冗余存储。`list_relations_with_changes` 做 top-N 排序。

### D4. as_of retrieval 参数

`build_runtime_retrieval_package_from_db(as_of=<iso>)` 把 `_build_recent_changes` 过滤到 `applied_at <= as_of`。**as_of 请求不读 / 不写 cache**（避免污染）。其他字段（participants/memories/relations）暂时仍是"当下视图"，完整历史重建留待 Phase 16+。

### D5. memory_recall_event 作为 self_activation 的第三分支

`services/memory_recall_service.recall_anniversary_memories` 扫描 active memory，若 `created_at` 距今 ∈ `{30, 90, 180, 365}` 天且 relevance ≥ 0.6，生成 `memory_recall_event`（source_type=self_activation）。受 `DEFAULT_RECALL_DAILY_BUDGET=2` 约束。

### D6. event_causality 边

migration 0010 新增 `event_causality(edge_id, cause, effect, confidence, reason, source)`。`services/event_causality_service.infer_event_causality` 喂近 15 条事件给 LLM，解析 `{edges: [{cause, effect, reason, confidence}]}` 并落边。source='llm'，便于日后扩 manual/rule。

### D7. 两个新 CLI

- `scripts/timeline.py --person-id`: persona_history + active_relations + recent_events
- `scripts/relation_timeline.py --relation-id --bucket`: strength 时序

## 后果

### 正面

- persona 轨迹与当前状态分离，既能看"当下"也能看"来路"
- as_of retrieval 打开了"回忆过去某时的场景"的门
- 事件因果链让图谱从"记录 happen 什么"进阶到"解释 why"
- 不改动 snapshot 语义，兼容性好

### 负面 / 权衡

- as_of 当前只过滤 recent_changes，relations / memories / states 仍是现时，完整 point-in-time 重建需要基于 snapshot_entities 回放
- event_causality 依赖 LLM 输出质量，没有 pre-existing 规则守卫
- persona_history 每次 drift 都写，长期积累需配合 Phase 8 的 cold_memories 模式做 cold 归档

### 后续

- Phase 16 多模态导入可把音视频事件也纳入因果推理
- Phase 17 what-if 的 simulate 可读 persona_history 做更准推演
- 更完整的 as_of 重建：基于 `snapshot_entities` 回放至 as_of 时刻
