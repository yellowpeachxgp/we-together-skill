# Release Notes — v0.19.0 (2026-04-22, local)

**Theme**: 从“功能存在”走向“生产化可验证”

**Local baseline**: 853 passed, 4 skipped；以 `docs/superpowers/state/current-status.md` 的最新代码事实为准
**ADR 总数**: 73
**不变式**: 28
**Migrations**: 21

## 本版核心变化

### 1. 真向量后端生产化

- `sqlite_vec` / `faiss` 不再是 stub
- `pyproject.toml` 新增 `vector` extra
- `bench_scale.py` 支持 archive / compare / `--backend all`
- 已归档 `100k / 1M` compare 报告
- 当前大规模默认推荐 backend：`faiss`

### 2. 联邦写路径进入生产 smoke

- `POST /federation/v1/memories`
- `event -> patch -> snapshot` 写入闭环
- `federation_e2e_smoke.sh` 覆盖：
  - capabilities
  - bearer 鉴权
  - invalid payload 422
  - create memory 201
  - list memories 200

### 3. 年运行审计增强

- `simulate_year.py` 支持：
  - `--provider`
  - `--dry-run-provider-check`
  - `llm_usage`
  - `estimated_cost_usd`
  - `monthly_reports`

### 4. 多租户基线大幅收口

tenant 路由已覆盖：

- 初始化 / seed
- 高频导入 / 建组
- scene / retrieval / summary
- MCP / dashboard / dialogue / host smoke
- 运维 / 修复 / maintenance / scenario / multi-agent
- timeline / rollback / activation / world / merge / branch
- analyze / eval / media import / graph_io / onboarding

并补充：

- `normalize_tenant_id()`
- invalid tenant 拒绝
- default vs alpha cross-tenant 负向测试
- tenant introspection in summary surfaces

## 本地收口已完成

- `pyproject.toml` version = `0.19.0`
- `src/we_together/cli.py` VERSION = `0.19.0`
- wheel 已 build：`dist/we_together-0.19.0-py3-none-any.whl`
- 隔离 venv 安装验证通过
- `twine check` 通过
- 本地 git tag：`v0.19.0`

## 仍未完成 / 外部依赖

以下项仍依赖外部条件，当前不宣称已完成：

- 真 provider 7-day / 30-day / 365-day 年运行实测
- PyPI 正式发布
- remote push / GitHub Release

## 关键文档

- [Phase 65-70 synthesis ADR](superpowers/decisions/0073-phase-65-70-synthesis.md)
- [Phase 65-70 progress snapshot](superpowers/state/2026-04-22-phase-65-70-progress.md)
- [Current status](superpowers/state/current-status.md)
- [Scale bench report v2](superpowers/state/2026-04-19-scale-bench-v2-report.md)
