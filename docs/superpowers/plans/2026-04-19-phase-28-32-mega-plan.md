# Phase 28-32 Mega Plan — Vector Scale + Multi-Agent + Proactive + Meta-cognition + Multimodal

**Date**: 2026-04-19
**Version target**: v0.13.0
**Test target**: 436 passed
**Status**: ✅ Delivered

## 战略图

| Phase | 主题 | Slice | 交付 |
|-------|------|-------|------|
| 28 | 向量规模化 | VI-1/2/3/5/6/8/9 | VectorIndex / EmbeddingLRUCache / Backend / NATS drain / cluster embedding-first |
| 29 | 多智能体 | MA-1/2/3 | PersonAgent / private vs shared / turn-taking |
| 30 | 主动图谱 | PG-1/2/3/4 | Trigger 三类 / Intent generate+execute / 预算 / 偏好 |
| 31 | 元认知 | MC-1/6 | contradiction_detector / benchmark + eval |
| 32 | 多模态 | MN-1/3 | MockMultimodalClient / CLIPStub / cross_modal cosine |

## 不变式扩展（ADR 0033）
16 → 18 条。新增：
- **#17**：多 agent 共享底层图谱真理，不内置 memory store 拷贝
- **#18**：主动写入必须经预算 + 偏好门控

## Slice 切片清单（约 100 task）
完整 ID 列表见 TaskList #475-#575。关键里程碑：

### Phase 28
- VI-1 VectorIndex（flat_python + filter） ✅
- VI-2 retrieval rerank（query_text + embedding_client） ✅
- VI-3 hierarchical recall（filter_person_ids） ✅
- VI-5 EmbeddingLRUCache（批级 dedup） ✅
- VI-6 Backend（SQLite + PG stub） ✅
- VI-8 cluster embedding-first（jaccard fallback） ✅
- VI-9 NATS drain（subscribe + timeout） ✅
- VI-4 1M 压测：⏭️ 留 v0.14（CI 不跑）
- VI-7 PyPI testpypi：⏭️ 需 token

### Phase 29
- MA-1 PersonAgent.from_db ✅
- MA-2 private vs shared 过滤 ✅
- MA-3 turn-taking next_speaker / orchestrate ✅
- MA-5 multi_agent_chat.py REPL：⏭️ 留 v0.14

### Phase 30
- PG-1 Trigger（anniversary / silence） ✅
- PG-3 Intent generate / execute / budget ✅
- PG-4 偏好 mute/consent + migration 0014 ✅
- PG-5 intents CLI / PG-6 simulate_week：⏭️ 留 v0.14

### Phase 31
- MC-1 contradiction_detector（two-stage） ✅
- MC-6 benchmark + eval（P/R） ✅

### Phase 32
- MN-1 Mock + CLIPStub ✅
- MN-3 cross_modal_similarity ✅
- 真 CLIP / media_assets 迁移：⏭️ v0.14

### EPIC
- EPIC-1 mega-plan ✅
- EPIC-2 CHANGELOG v0.13.0 ✅
- EPIC-3 README ✅
- EPIC-4 graph_summary diff ✅
- EPIC-5 git tag v0.13.0 ✅
- EPIC-6 ADR 0033 综合 ✅
- EPIC-13 全量回归 + commit ✅

## 验收

```bash
.venv/bin/python -m pytest -q
# expected: 436 passed
```

```bash
git tag v0.13.0
```

## 与 vision 对齐

- **A 严格工程化**：18 条不变式、双路径、延迟 import、零硬依赖膨胀
- **B 通用型 Skill**：所有 Phase 28-32 新能力都不破坏 SkillRuntime 接口
- **C 数字赛博生态圈**：多智能体 + 主动 + 元认知 = 图谱有了"自我"

## 拒绝清单
- 真 sqlite-vec / FAISS 集成（CI 不稳）→ 留 v0.14
- 真 cron daemon → 让宿主调度
- contradiction 自动改图 → 违反不变式 #18
