# ADR 0025: Phase 26 — 向量化图谱（Embedding-First Graph）

## 状态
Accepted — 2026-04-19

## 背景
Phase 24 的 associative_recall 是 LLM 提示从候选池挑，靠字面理解。memory_cluster 用 Jaccard 对 owners 聚类。这两者离"语义"都还很远。

## 决策

### D1. EmbeddingClient Protocol
`llm/providers/embedding.py`: `EmbeddingClient` 暴露 `embed(texts) -> list[list[float]]`。`MockEmbeddingClient`（hash 确定性）+ `OpenAIEmbeddingClient` + `SentenceTransformersClient`（延迟 import）。

### D2. migration 0013 三张 embedding 表
`memory_embeddings` / `event_embeddings` / `person_embeddings`：`(id PK, model_name, dim, vec BLOB, created_at)`。BLOB 为 struct packed float32。

### D3. vector_similarity 纯 Python
`services/vector_similarity`: `encode_vec` / `decode_vec`（float32 struct）+ `cosine_similarity` + `top_k`。规模大时建议替换为 FAISS / chromadb。

### D4. associative_recall 升级
`services/embedding_recall.associate_by_embedding`：替代 LLM stub；无 embedding 索引时返回 `reason=no_embeddings_indexed`，调用方可 fallback 到旧 LLM 联想。

### D5. embed_backfill CLI
`scripts/embed_backfill.py --target memory|event|person`：给历史数据批量补算 embedding。默认 MockEmbedding；--provider openai / sentence-transformers 可切。

### D6. Embedding retrieval eval benchmark
`benchmarks/embedding_retrieval_groundtruth.json`：主题 seed → 期望 memory_ids；`eval/embedding_retrieval_eval` 跑 pass_rate。

## 后果
正面：图谱从字面匹配进入语义时代；可渐进式替换 Jaccard cluster 与 LLM 联想；backfill CLI 让历史数据一次性迁移。
负面：MockEmbedding 是 hash，对 eval 质量无实际信号；真 embedding 需要 API key；BLOB 不支持 SQLite 原生向量检索（需全扫）。

## 后续
- Phase 28+：SQLite 向量插件（sqlite-vec）或 FAISS 索引
- memory_cluster 默认改用 embedding（当前保留 Jaccard fallback）
- retrieval_package 按 query embedding 重排（VE-6 预留）
