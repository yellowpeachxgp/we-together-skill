---
adr: 0068
title: Phase 67-69 — 联邦写路径 + 生产 HTTP Smoke + 年运行 LLM 审计
status: Accepted
date: 2026-04-19
---

# ADR 0068: Phase 67-69 — 联邦写路径 + 生产 HTTP Smoke + 年运行 LLM 审计

## 状态
Accepted — 2026-04-19

## 背景

在 v0.18 之后，项目已经具备：

- 真 `sqlite_vec / faiss` backend
- 联邦 HTTP 只读接口
- `simulate_year` 年运行骨架

但要推进到 v0.19，还缺三条关键闭环：

1. **联邦只能读不能写**，生态圈仍停留在“看见彼此”，还不能“安全地互相写入共享记忆”。
2. **HTTP 生产 smoke 只有手工命令，没有脚本化证据**，不利于 release / nightly / 无人值守工作流。
3. **年运行没有 LLM usage/cost 审计**，即使接了真 provider，也无法给出可核查的成本证据。

## 决策

### D1. 联邦写路径默认关闭，显式开启

`POST /federation/v1/memories` 只在 `--enable-write` 打开时可用。

默认仍保持：

- 读路径开放（可带 token）
- 写路径关闭

理由：

- 写路径的风险显著高于读路径。
- 生产部署必须显式声明“这台实例允许被远端写入”。

### D2. 联邦写入必须走 event-first

联邦写路径采用固定闭环：

```text
HTTP POST
-> create federation event
-> build_patch(create_memory)
-> apply_patch_record
-> write memory_owners
-> build snapshot + snapshot_entities
```

明确禁止：

- 直接在 HTTP handler 里 `INSERT memories`
- 直接写 memory 而不落 event / patch / snapshot

### D3. 联邦写逻辑抽到 service，而不是塞进 handler

新增：

- `src/we_together/services/federation_write_service.py`

原因：

- HTTP 只是 transport。
- 真正的业务约束是 event-first / patch-first。
- 后续 CLI 或其他宿主若也要走联邦写，不应复制逻辑。

### D4. capabilities 必须反映 write mode

`/federation/v1/capabilities` 增加：

- `read_only`
- `write_enabled`

避免出现：

- server 已启用写路径
- capabilities 却仍宣称只读

### D5. 生产 HTTP smoke 必须脚本化

新增：

- `scripts/federation_e2e_smoke.sh`

覆盖：

1. `GET /capabilities`
2. 未鉴权 `GET /persons` → 401
3. Bearer `GET /persons` → 200
4. Bearer `POST /memories` → 201
5. Bearer `GET /memories` → 200

### D6. 年运行必须有 usage / cost 审计

新增：

- `src/we_together/llm/audited_client.py`
- `scripts/simulate_year.py` 的：
  - `--provider`
  - `--dry-run-provider-check`
  - `llm_usage`
  - `estimated_cost_usd`

规则：

- provider 若返回原生 usage，就用原生 usage。
- 否则回退到字符级估算。

这保证：

- mock provider 也能形成审计骨架
- 真 provider 时可以给出更可信的 token/cost 统计

### D7. Nightly 进入 native backend 模式

`nightly.yml` 改为：

- 安装 `.[vector]`
- 跑 `sqlite_vec` / `faiss` benchmark
- 上传 `benchmarks/scale/` + `benchmarks/tick_runs/`

## 版本锚点

- 新 service: `federation_write_service.py`
- 新 script: `federation_e2e_smoke.sh`
- 新 wrapper: `llm/audited_client.py`
- 更新：`federation_http_server.py` / `federation_client.py` / `simulate_year.py`
- 测试基线：**708 passed, 4 skipped**

## 非目标

- 联邦写路径的 mTLS / JWT / signed requests
- 远端写入 relation / person / scene
- `dream_cycle` 真 LLM insight 生成
- 真 LLM 365 天大预算运行归档

## 拒绝的备选

### 备选 A：让联邦写路径默认开启

拒绝原因：生产安全边界过宽。

### 备选 B：直接在 HTTP handler 里插入 memories

拒绝原因：违反 event-first / patch-first 设计，破坏可审计性。

### 备选 C：等真 provider 接上后再补 usage 审计

拒绝原因：会把“成本治理”继续拖成纸面工作，违背 A 支柱。

## 下一步

1. 给联邦写路径补更多 curl / rate-limit / invalid-payload smoke。
2. 给 `simulate_year` 增加月度 usage/cost report artifact。
3. 做 100k / 1M compare benchmark，把 native backend 证据补齐。
