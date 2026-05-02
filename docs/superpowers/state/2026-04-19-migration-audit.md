# Migration Audit (v0.14.0, Phase 36)

**Date**: 2026-04-19
**目标**：审计 14 条 migrations 的热路径使用情况，识别"写了但没读"的死表。

## Migrations 审计表

| Migration | 表 | 写路径 | 读路径 | 状态 |
|-----------|------|--------|--------|------|
| 0001_initial_core_schema | persons / relations / scenes / memories / memory_owners / events / patches / snapshots | 所有 importer / patch_applier | retrieval_package / CLI | 🟢 核心 |
| 0002_connection_tables | scene_participants / scene_active_relations / group_members / event_participants / event_targets | importer / scene_service | retrieval | 🟢 核心 |
| 0003_trace_and_evolution | raw_evidence / import_jobs / local_branches / branch_candidates / snapshot_entities | importer / fusion | branch_resolver / rollback | 🟢 核心 |
| 0004_indexes_and_constraints | (indexes) | — | 查询加速 | 🟢 核心 |
| 0005_runtime_cache | retrieval_cache | runtime/sqlite_retrieval | retrieval_package 缓存 | 🟢 核心 |
| 0006_candidate_layer | identity_candidates / event_candidates / facet_candidates / relation_clues / group_clues | LLM extraction / importer | fusion_service | 🟢 核心 |
| **0007_cold_memories** | cold_memories | memory_archive_service.archive | cold_memory CLI + 搜索 | 🟡 **低热**但保留 |
| 0008_external_person_refs | external_person_refs | federation_fetcher (stub) | 联邦 stub | 🟡 stub 依赖，留到 v0.15 真联邦时评估 |
| 0009_persona_history | persona_snapshots | persona_drift_service | persona_history_service | 🟢 次路径 |
| **0010_event_causality** | event_causes / event_effects | event_causality_service | graph_analytics / narrative | 🟡 **低热**但保留（narrative 用） |
| 0011_narrative_arcs | narrative_arcs / narrative_chapters | narrative_service | narrate CLI | 🟢 核心（CLI 入口） |
| **0012_perceived_memory** | perceived_memories / perceived_memory_events | perceived_memory_service | 多视角 memory | 🟡 **低热**但保留 |
| 0013_embeddings | memory_embeddings / event_embeddings / person_embeddings | embedding_recall / embed_backfill | vector_index / associate_by_embedding | 🟢 核心 |
| 0014_proactive_prefs | proactive_prefs | proactive_prefs.set_mute/consent | proactive_agent.is_allowed | 🟢 核心 |
| 0015_media_assets | media_assets / media_refs | media_asset_service / ocr_service | list_by_owner / link_to_memory | 🟢 核心（新） |

## 低热 migration 决策
三条低热 migration（0007 / 0010 / 0012）都有至少一个 service 写、一个 service 读，**不是 dead schema**。本阶段全部保留。

如果 v0.15 真部署后发现它们**零被 retrieval 命中**，可以走：
1. 加 deprecation 注释（migration 头部）
2. 下一个大版本（v0.20）真删除 + 对应 service

## 不变式加强
任何新 migration **必须同时说明写路径与读路径**（在 ADR 里显式列出）；否则不能合并。

## 相关 ADR
- ADR 0033 synthesis 18 条不变式，本次审计属于 A 支柱"严格工程化"
- 新不变式 #19 / #20（见 ADR 0038）
