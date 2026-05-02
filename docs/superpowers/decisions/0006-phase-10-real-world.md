# ADR 0006: Phase 10 — 真实世界数据化（Real-world Ingestion）

## 状态

Accepted — 2026-04-18

## 背景

Phase 4 的 llm_extraction + Phase 7 的 wechat_text CSV 让图谱第一次接触真实文本，但仍离"吃真人数据"有显著距离：iMessage 本地 chat.db、微信 db（解密后）、邮件 MBOX 批量、图片/截图、社交公开数据这五类高价值来源均未覆盖。

## 决策

### D1. iMessage / 微信 db / MBOX 三个只读 sqlite-或 mbox importer

- `importers/imessage_importer.import_imessage_db(chat_db)` 兼容 macOS chat.db 核心子集（message/handle/chat/chat_message_join）。
- `importers/wechat_db_importer.import_wechat_db(db_file)` 只支持明文 sqlite；加密路径委派外部工具（例如 ex-skill/wechat_decryptor），保持本仓"无外部密钥依赖"。
- `importers/mbox_importer.import_mbox(mbox_file)` 使用标准库 mailbox。

三者统一输出 `{identity_candidates, event_candidates, source, ...}`，由 fusion_service 负责后续升级。**均不直接改主图**。

### D2. VLM 抽取走独立 provider 通道

新增 `llm/providers/vision.py`：`VisionLLMClient` Protocol + `MockVisionLLMClient`（scripted / default 描述）+ `AnthropicVisionClient`（延迟 import anthropic SDK）。`importers/image_importer.import_image(path, vision_client)` 调 `describe_image` 获取文本，产出 `image_event` candidate。真实实体抽取让下游 `llm_extraction_service` 二次处理。

### D3. 社交公开数据走统一 JSON 中间层

`importers/social_importer.import_social_dump(json_path)` 接收以下结构（与任何上游采集工具解耦）：
```
{platform, owner_handle, posts: [{id, text, mentions, created_at}],
 following: [...], followers: [...]}
```
产出 identity_candidates + social_post event_candidates。不主动抓网，所有网络 I/O 留给上游工具完成。

### D4. Evidence 去重以 content_hash 辅助表实现

`services/evidence_dedup_service`：`compute_evidence_hash(content, source_name)` 用 SHA-256，`evidence_hash_registry` 辅助表提供 `is_duplicate` / `register_evidence_hash`。**不破坏现有 raw_evidence schema**，追加表形式引入，便于后续 migration 演进。

## 后果

### 正面

- 5 个真实世界来源 importer 同一契约，测试覆盖 6 个
- AnthropicVisionClient 延迟 import，CI 无需 API Key
- 去重能力是所有 importer 共享的基础设施
- 微信加密路径显式下沉，保持本仓边界清晰

### 负面 / 权衡

- iMessage/微信 db 的真实 schema 随系统版本漂移，测试只覆盖核心子集
- social_importer 依赖上游采集工具提供标准 JSON，目前没有官方工具可复用
- evidence_hash 是辅助表而非主 schema 字段，未来需要规范化（Phase 12 HD-6 schema 版本检测会提示）

### 后续

- Phase 11 的联邦引用会复用 social_importer 的 handle 归一化
- Phase 12 会把 evidence_dedup 提升为 migration 0008 的正式字段
