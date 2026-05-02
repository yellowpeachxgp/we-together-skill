---
adr: 0050
title: Phase 48 — 联邦安全 + PII 脱敏
status: Accepted
date: 2026-04-19
---

# ADR 0050: Phase 48 — 联邦安全 + PII 脱敏

## 状态
Accepted — 2026-04-19

## 背景
ADR 0044 的 Federation Protocol v1 MVP 无鉴权、无速率限制、无 PII 保护——无法真部署到公网。v0.16 升到 v1.1 补齐这三道门槛。

## 决策

### D1. Bearer Token 鉴权
- 服务端读 `WE_TOGETHER_FED_TOKENS` env var（逗号分隔的原始 token 字符串）
- 存储 hash（sha256）；对比用 `hmac.compare_digest`（防 timing attack）
- 无 token 配置时 → 开放（向后兼容 v1 行为）
- `/capabilities` 不需要鉴权（用于发现服务能力）
- 其他 endpoint 401 rejected if token invalid

### D2. Rate Limit
- `RateLimiter(max_per_minute, window_seconds)` 内存滑动窗口
- per-token-key 分桶；未鉴权时 key='anonymous'
- 超限返回 `429 {error: "rate_limited", retry_after_seconds: 60}`

### D3. PII 脱敏
- `mask_email`：`alice@corp.com` → `a***@corp.com`
- `mask_phone`：`13812345678` → `***5678`（保留后 4 位）
- `sanitize_record(record, fields)`：默认脱敏 summary / primary_name / note / description / metadata 字段
- 服务端默认开启；`--disable-pii-mask` 可关

### D4. Visibility Policy
- `is_exportable(record)`：
  - `metadata.exportable=False` → 不导出
  - `visibility='private'` → 不导出
  - 其他 → 可导出
- `/persons/{pid}` 遇不可导出返 404（不泄露存在性）

### D5. FederationClient 升级
- 新增 `bearer_token: str | None = None` 字段
- 有 token 则自动加 `Authorization: Bearer <token>` header

### D6. 协议升级 v1 → v1.1
- `/capabilities` 声明 `federation_protocol_version: "1.1"`
- 新增字段：`pii_masking: true`、`rate_limit_per_minute: 60`、`auth: "bearer (optional)"`
- 向后兼容：v1 client 读不到新字段也能跑

## 不变式（新，v0.16 第 25 条）
**#25**：任何跨进程 / 跨图谱出口（联邦 / 导出）必须支持 PII 脱敏与 visibility 过滤。
> 违反则隐私数据被导出到其他 skill；合规性崩塌。

## 版本锚点
- tests: +12 (test_phase_48_fs.py)
- 文件: `services/federation_security.py` / 更新 `federation_http_server.py` + `federation_client.py`
- Phase 42 测试更新 `v1` → `in ("1", "1.1")` 兼容

## 非目标（v0.17）
- mTLS 鉴权（需证书管理）
- OAuth 2.0 flow
- 写路径（需更强鉴权设计）
- 全局 rate limit（当前 per-token 即够）
- audit log 持久化（当前仅 in-memory）
- 敏感字段分级（secret / pii / internal / public）

## 拒绝的备选
- JWT：签名/验证复杂；Bearer 足够 v0.16 场景
- redis rate limiter：引依赖；in-memory 够本阶段
- 自动检测 PII 类型（ML）：误检风险；显式正则更可控
- 在 database 列里加 `exportable` 布尔：太重；用 metadata.exportable 即可
