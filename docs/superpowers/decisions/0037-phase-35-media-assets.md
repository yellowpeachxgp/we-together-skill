---
adr: 0037
title: Phase 35 — 媒体资产落盘
status: Accepted
date: 2026-04-19
---

# ADR 0037: Phase 35 — 媒体资产落盘

## 状态
Accepted — 2026-04-19

## 背景
Phase 32 多模态只写了 teaser（Mock/CLIP stub + cross_modal cosine）——骨架在，但图谱本身不存任何媒体。这让"人物记忆不只有文本"的 vision 无从落地。Phase 35 把媒体资产真正写进图谱。

## 决策

### D1. Migration 0015_media_assets
两张新表：
- `media_assets(media_id, kind, path, content_hash, mime_type, size_bytes, owner_type, owner_id, visibility, scene_id, summary, metadata_json, created_at, updated_at)`
- `media_refs(media_id, target_type, target_id)` 多对多关联到 memory / event

hash dedup 索引 + owner 索引 + scene 索引。

### D2. media_asset_service 作为 canonical 入口
- `register(kind, content, owner_id, visibility, scene_id, summary, ...)`
- hash-dedup 规则：同 owner 下同 content_hash 返回旧 media_id
- `list_by_owner` / `list_by_scene` / `link_to_memory` / `link_to_event`
- `filter_by_visibility(items, viewer_id)`：retrieval 层过滤 private

### D3. ocr_service / audio_transcribe 作为高阶接入
- `ocr_to_memory(db, image_bytes, owner_id, scene_id, vision_client)`：
  vision 描述 → register media → INSERT memory + memory_owners → link
- `transcribe_to_event(db, audio_bytes, owner_id, ..., transcriber)`：
  转录 → register media → INSERT event → link
- 都走 Mock client 默认，真 client 在 extra 下延迟 import

### D4. CLI
- `scripts/import_image.py` 单图导入
- `scripts/import_audio.py`（已存在，本阶段实装）

### D5. benchmark
- `benchmarks/multimodal_retrieval_groundtruth.json` v1：text query → image relevant/irrelevant

## 非目标（留 v0.15+）
- patch 化媒体导入（当前 ocr_to_memory / transcribe_to_event 是直接 INSERT，属于"单一 importer"行为；未来要走 event → patch）
- media embedding 入 memory_embeddings 做跨模态联合召回（需要 dim 对齐的 multimodal client，当前 Mock 已可跑）
- Skill prompt 自动带图片 URL（需 vision-capable adapter）

## 版本锚点
- tests: +8 (test_phase_35_media.py)
- migration: 0015
- benchmark: multimodal_retrieval_groundtruth (第 9 个)

## 拒绝的备选
- 把媒体嵌入 memories 表的 summary 字段：会毁 schema；独立表更清晰
- 媒体存 base64 入库：size 暴涨；只存 path + hash，真文件由宿主负责
