---
adr: 0044
title: Phase 42 — 联邦 MVP（Federation Protocol v1 / Read-Only）
status: Accepted
date: 2026-04-19
---

# ADR 0044: Phase 42 — 联邦 MVP

## 状态
Accepted — 2026-04-19

## 背景
v0.10 的 `federation_service` + `federation_fetcher` 是 stub；`docs/superpowers/specs/federation-protocol.md` 只有 RFC draft。要让"生态圈"真能互联，需要：
1. 真 HTTP endpoint（两端都能拉）
2. 协议版本化
3. 明确 Read-Only 边界（写路径太复杂，留 v0.16）

## 决策

### D1. Federation Protocol v1（Read-Only）
见 `docs/superpowers/specs/federation-protocol-v1.md`。
- `federation_protocol_version="1"`
- 4 个 endpoint：`/capabilities` / `/persons` / `/persons/{pid}` / `/memories`
- 只读；只返 `status='active'` + `is_shared=1`
- v1 MVP：**无鉴权**（localhost / VPC 级别用）

### D2. HTTP server 骨架
- `scripts/federation_http_server.py`
- Python stdlib `http.server`；不引 FastAPI
- `--host 127.0.0.1 --port 7781` 默认

### D3. Client
- `services/federation_client.py`
- 纯 `urllib.request`；不引 httpx
- `FederationClient(base_url).capabilities() / list_persons() / get_person(pid) / list_memories()`

### D4. 身份映射留在上层
- `federation_service.register_external_person()` 已存在
- 客户端只拉数据，**不**自动 register；由 skill 的 fusion / identity service 决定
- 遵守不变式 #18（不自动改图）

### D5. 与 Skill Schema v1 的关系
服务端返回 skill_schema_version=1；不变式 #19 保证跨版本互操作前 v2 发布有显式切换点。

## 非目标（留 v0.16）
- 写端点（POST/PUT）
- 鉴权（mTLS / Bearer）
- rate limiting
- visibility policy 细粒度（`exportable: false` 等）
- cross-graph identity fusion（真把远端 person 合到本地）
- 失败重试 / 退避 / 缓存

## 版本锚点
- tests: +6 (test_phase_42_fd.py)，含真 HTTP e2e roundtrip
- 文件: `scripts/federation_http_server.py` / `services/federation_client.py` / spec-v1.md
- 跨模块联动：`runtime.skill_runtime.SKILL_SCHEMA_VERSION` 出现在 `/capabilities`

## 拒绝的备选
- FastAPI / Starlette：引入依赖；stdlib 够用
- gRPC：v1 先让 HTTP 跑起来，gRPC 可 v0.17
- 引入 JWT：MVP 没有用户概念；v0.16 配鉴权时再议
- 写端点：会打破 Read-Only 心智模型，不值得做一半
