---
adr: 0032
title: Phase 32 — Multimodal Native (Teaser)
status: Accepted
date: 2026-04-19
---

# ADR 0032: Phase 32 — 多模态原生（teaser）

## 状态
Accepted — 2026-04-19

## 背景
未来人物记忆不只有文本（语音、照片、表情包）。Phase 32 在不引入硬依赖的前提下，搭好"**跨模态共享 embedding 空间**"的骨架：CLIP/SigLIP 风格的 text↔image 接口 + cosine top-k 跨模态检索。

## 决策

### D1. MultimodalEmbeddingClient Protocol（MN-1）
- `llm/providers/multimodal_embedding.py`
- Protocol: `embed_text(texts) / embed_image(images) → list[list[float]]`，共享 `dim` 维度
- `MockMultimodalClient(dim=32)`：sha256 hash → 维度归一，确定性可测
- `CLIPStubClient`：延迟 import `transformers`；缺包则 raise（CI 走 mock，真 client 在 vision extra）

### D2. 跨模态 cosine top-k（MN-3）
- `cross_modal_similarity(query_vec, candidates: list[(id, vec)], k)` → 排序 top-k
- query 是 text embedding，candidates 是 image embedding；同空间用 cosine
- 复用 `services/vector_similarity.cosine_similarity`，不发明新算法

### D3. 不写图谱（teaser 边界）
- Phase 32 仅提供能力骨架；不接 retrieval / 不改 schema
- 真接入留待 v0.14（要新 migration: `media_assets` 表 + image embedding 存储）

## 版本锚点
- tests: +3（mock_multimodal / clip_stub_requires / cross_modal_topk）
- extras: 已有 `[vision]` extra；CLIPStubClient 是占位

## 拒绝的备选
- 直接接 transformers：硬依赖太重，CI 拒绝
- 把 image embedding 塞进 memory_embeddings：dim/model 不一致，要先设计独立表
