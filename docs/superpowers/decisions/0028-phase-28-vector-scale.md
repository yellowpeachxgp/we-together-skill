---
adr: 0028
title: Phase 28 — Vector Index & Scale
status: Accepted
date: 2026-04-19
---

# ADR 0028: Phase 28 — Vector Index & Scale

## 状态
Accepted — 2026-04-19

## 背景
Phase 26 引入了 embedding（v0.11.0），但 retrieval 仍是 O(N) 全扫；缓存零；后端只有 SQLite；NATS drain 是占位；memory cluster 走 jaccard。Phase 28 目标：把"向量化图谱"从 demo 推向**规模可用**。

## 决策

### D1. VectorIndex（VI-1）：flat_python + 层级
- `services/vector_index.py`：`VectorIndex(backend="flat_python")` 提供 `add_batch / search(top_k) / search_with_filter(person_ids)`
- `flat_python` 是基线后端，O(N) 但纯 Python；后续接 sqlite-vec/FAISS 时只需新增 backend 字符串
- 层级查询 = 先用 person filter 缩集，再 cosine top-k

### D2. 重排 + 层级检索（VI-2/VI-3）
- `runtime/sqlite_retrieval.build_runtime_retrieval_package_from_db()` 新增 `query_text`/`embedding_client` 参数
- 命中即对 `relevant_memories` 做 embedding rerank，未命中沿用原 score
- `embedding_recall` 增加 `filter_person_ids` → 走 VectorIndex 层级路径

### D3. 缓存（VI-5）：批级 dedup
- `services/embedding_cache.py: EmbeddingLRUCache(maxsize=1000)`
- `embed_with_cache(client, texts)` 在批内部去重：同一批内重复输入算 hit
- 暴露 `hit_count / miss_count` 用于 metrics

### D4. Backend 抽象（VI-6）
- `db/backends.py`：`SQLiteBackend`（默认）+ `PGBackend`（延迟 import psycopg）
- 业务代码继续走 `db.connection.connect`；Backend 是 v2 候选适配层，不强制切换

### D5. Cluster embedding-first（VI-8）
- `memory_cluster_service.cluster_memories(use_embedding=True)`：embedding 命中走 cosine 阈值，否则 fallback Jaccard
- 保证旧测试（无 embedding）继续 green

### D6. NATS drain 真实现（VI-9）
- `event_bus_service.NATSBackend.drain()`：subscribe + asyncio timeout 收集消息再 unsubscribe
- 真 NATS 不在 CI；mock backend 仍是单测主路径

## 不变式增量
（在 ADR 0027 16 条基础上追加，参见 ADR 0033）

## 版本锚点
- tests: 419 passed（+9 Phase 28 测试）
- 文件新增: vector_index.py / embedding_cache.py / db/backends.py
- 旧路径不破坏：`embedding_recall` 默认 `filter_person_ids=None` 走原路径

## 拒绝的备选
- 直接接 sqlite-vec：CI 环境不稳定，留作 v0.14 候选
- 索引常驻进程：与 SkillRuntime "无状态优先" 矛盾
