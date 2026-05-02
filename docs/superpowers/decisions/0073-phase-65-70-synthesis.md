---
adr: 0073
title: Phase 65-70 综合 — 向量生产化、联邦写路径、LLM 审计、多租户基线
status: Accepted
date: 2026-04-22
---

# ADR 0073: Phase 65-70 综合 — 向量生产化、联邦写路径、LLM 审计、多租户基线

## 状态
Accepted — 2026-04-22

## 背景

v0.18.0 之后，项目的下一步不是横向加很多新 feature，而是把几个长期停留在“已经设计好、但仍不够生产化”的方向真正做实：

1. `sqlite_vec / faiss` 从 stub 变成可安装、可验证、可归档的真实 backend。
2. 联邦从 read-only demo 进入 write path + curl smoke。
3. `simulate_year` 从“能跑”进入“可审计 usage/cost / 月报”。
4. `tenant_router` 从一个路径 helper 变成真正贯穿 CLI / 宿主 / 运维脚本的多租户基线。

## 决策

### D1. 向量后端进入生产化状态

Phase 65-66 做成了三层证据：

- 安装：`pyproject.toml` 有 `vector` extra
- 代码：`sqlite_vec` / `faiss` 真 backend
- 证据：`100k / 1M` compare 归档 + 报告

结论：

- `auto -> flat_python` 继续保持稳定语义
- `faiss` 是当前 100k / 1M 的默认推荐 backend
- `sqlite_vec` 是明显优于 `flat_python` 的 SQLite 内方案

### D2. 联邦写路径采用显式开启 + event-first

`POST /federation/v1/memories`：

- 默认关闭
- `--enable-write` 显式开启
- 写入闭环：`event -> patch(create_memory) -> owners -> snapshot`

并通过 `scripts/federation_e2e_smoke.sh` 做生产风格验证。

### D3. 年运行必须可审计

`simulate_year.py` 现在不仅输出年度总账，还输出：

- `llm_usage`
- `estimated_cost_usd`
- `monthly_reports`

这样真 provider 接入后，成本治理不会再次沦为纸面承诺。

### D4. 多租户基线已经进入“真实入口覆盖”

tenant 不再只存在于 `tenant_router` 和少数脚本里，而是已经扩展到：

- 初始化 / seed
- 导入 / 建组 / scene / retrieval / summary
- MCP / dashboard / dialogue / host smoke
- simulate / dream / fix / maintenance
- snapshot / world / branch / merge / activation / timeline
- analyze / eval / media import / graph_io / scenario / multi-agent

同时补了：

- `normalize_tenant_id()`
- invalid tenant 拒绝
- default vs alpha 的 cross-tenant 负向测试

### D5. 明确 tenant rollout 的边界

不是所有 `--root` 都该 tenant 化：

- `package_skill.py`：不应 tenant 化
- `demo_openai_assistant.py`：当前不应 tenant 化
- `bench_scale.py`：暂缓，等更安全的 benchmark contract

## 版本锚点

- ADR 0067-0073
- 当前本地基线：**761 passed, 4 skipped**
- 当前 `self_audit`：**73 ADR / 28 invariants / 83 services / 68 scripts / 21 migrations**

## 未完成 / 外部依赖

以下项仍依赖外部条件，不应伪装成“已完成”：

- 真 LLM 7 天 sample run
- 真 LLM 30 天 sample run
- 真 LLM 365 天大预算年报告
- remote push / GitHub Release / PyPI 发布

## 后果

### 正面

- A 支柱继续强化：更多能力进入“代码 + 测试 + 证据”闭环
- B 支柱强化：联邦 / 宿主 / 多租户入口更接近真实部署
- C 支柱强化：年运行与赛博生态圈的“长期运行”更可信

### 风险

- tenant 覆盖面大，后续新脚本若忘记复用 `tenant_router` 会再次漂移
- 真 provider 年运行仍未做，成本结论还只是框架级而不是实测级

## 下一步

1. 进入 Phase 71 EPIC 收口
2. 基于真实外部条件决定是否直接 bump 到 `0.19.0`
3. 若不立即发版，也应先把 release notes / current-status / README 收成可发布状态
