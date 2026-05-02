# ADR 0004: Phase 8 — 图谱活化（Neural Mesh）

## 状态

Accepted — 2026-04-18

## 背景

Phase 5-7 让系统具备了从导入到对话演化的完整闭环，但 runtime 仍是"单场景、单检索、单人物发言"的静态视图。与 `product-mandate.md` 第 C 条 "具备神经单元网格式激活与传播特征" 仍有明显差距。

## 决策

### D1. 多场景并发激活

`src/we_together/runtime/multi_scene_activation.py` 以 `build_multi_scene_activation(db_path, scene_ids)` 聚合多个 active scene 的 activation_map：person_id 去重、activation_state 取 priority 更高者、activation_score 取 max，并附带 `source_scenes` 指示激活来源。CLI 层 `build_retrieval_package.py --scenes s1,s2,...` 透传。

### D2. 记忆凝练 + 持续压缩

`memory_cluster_service.cluster_memories`：按 memory_type + owners Jaccard >= threshold 做 union-find 聚类。
`memory_condenser_service.condense_memory_clusters`：对 cluster 走 LLM 生成 summary，落 `condensed_memory` 类型 memory，`metadata_json.condensed_from` 保留原 refs。归入 daily_maintenance 的第 6 步。

### D3. Persona Drift

`persona_drift_service.drift_personas`：窗口内 events 喂给 LLM，蒸馏新的 persona_summary / style_summary，通过 `update_entity` patch 落地。归入 daily_maintenance 第 5 步。LLM 不可用时安静跳过。

### D4. 自发 pair 交互

`self_activation_service.self_activate_pair_interactions`：在 scene 活跃 persons 中挑 pair，生成 `latent_interaction_event`，两人均为 actor，同时写一条双人 owners 的 `shared_memory`。受 `DEFAULT_PAIR_DAILY_BUDGET` 约束。

### D5. 跨场景 Echo

`sqlite_retrieval._build_cross_scene_echoes`：在 retrieval_package 中新增 `cross_scene_echoes` 字段，列出其他 active scene 中 confidence >= 0.7 且非 private 的高权重 events。让当前 scene 感知邻接场景动态。

### D6. 冷记忆归档 + 恢复

migration 0007 新增 `cold_memories` / `cold_memory_owners` 表。`memory_archive_service.archive_cold_memories` 将长期 inactive 或低置信度 memory 移入冷存储；`restore_cold_memory` 支持反向恢复。retrieval 默认不读冷存储。

## 后果

### 正面

- 图谱从"被动问答"升级为"持续自演化"
- daily_maintenance 一次跑完六步：relation drift / state decay / branch auto-resolve / merge duplicates / persona drift / memory condense
- retrieval_package 现在显式包含跨场景感知能力
- 长期数据膨胀有对应归档策略

### 负面 / 权衡

- LLM 调用次数增加（persona drift + memory condense），需要 `--skip-llm` 开关应对 CI
- cross_scene_echoes 会让 retrieval_package 尺寸轻微增长，未压缩时约 +10%
- cold_memories 与 memories 双表治理需要后续补 retrieval 层的 include_cold 选项

### 后续

- Phase 9 会让 adapter 支持 tool_use，让 chat_service 能在自发 pair 事件里真正调工具
- Phase 11 会把 cold_memories 与联邦引用结合（外部 skill 查询冷记忆时才唤回）
