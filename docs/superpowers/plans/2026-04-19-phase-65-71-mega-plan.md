# Phase 65-71 Mega Plan — Vector Productionization + Massive Scale + Federation Write + Real LLM + Multi-World

**Date**: 2026-04-19
**Version target**: v0.19.0
**Mode**: 无人值守连续推进
**Task target**: 116 tasks
**Status**: 🟡 In Progress — Phase 65-70 基本完成，Phase 71 EPIC 待收口

## 战略图

| Phase | 主题 | Task IDs | 支柱 | 交付 |
|-------|------|----------|:---:|------|
| 65 | 向量生产化 | VP-1..18 | A + B | vector extras / 真 backend integration / archive bench / CI smoke |
| 66 | 100k-1M 规模证据 | SCX-1..18 | A + C | 100k / 1M bench / 三 backend 对比 / 报告归档 |
| 67 | 联邦写路径 | FW-1..18 | B + C | POST `/memories` / token / event-first write / client update |
| 68 | 生产 HTTP E2E + 观测 | HE-1..16 | A + B | curl suite / dashboard+metrics / release smoke / docs |
| 69 | 真 LLM 年运行 | LY-1..14 | C | simulate_year with real LLM / dream insight / cost report |
| 70 | 多 world / 多租户基线 | MW-1..14 | B + C | tenant routing hardening / namespace / cross-world contract |
| 71 | EPIC | EPIC-1..18 | 全局 | ADR 0067-0073 / CHANGELOG / current-status / release notes / bump + tag |

## 候选不变式（本轮按需落地）

- **#29 候选**：`auto` backend 不得随环境 silently drift；native backend 必须显式声明。
- **#30 候选**：联邦写路径必须走 event → patch → snapshot，不得直接写业务表。
- **#31 候选**：真 LLM 年运行必须输出可审计的 budget / usage / report artifact。

---

## Phase 65 — 向量生产化（18 tasks）

- `VP-1` 为 `pyproject.toml` 增加 `vector` optional extra：`sqlite-vec` / `faiss-cpu` / `numpy`
- `VP-2` 为 optional extra 写 packaging 测试，防止 release 忘带 native deps
- `VP-3` 给 `bench_scale.py` 增加 `--archive` / `--archive-dir`，复用现有归档风格
- `VP-4` 给 `bench_scale.py` 增加 backend metadata：`backend` / `platform` / `python_version`
- `VP-5` 给 `bench_scale.py` 增加 `build_report()` / `archive_report()` 可测试函数
- `VP-6` 给 `VectorIndex(sqlite_vec)` 加真实集成测试（环境装了就跑，没装就 skip）
- `VP-7` 给 `VectorIndex(faiss)` 加真实集成测试（环境装了就跑，没装就 skip）
- `VP-8` 给 `hierarchical_query(..., backend='sqlite_vec')` 增加真实集成测试
- `VP-9` 给 `hierarchical_query(..., backend='faiss')` 增加真实集成测试
- `VP-10` 给 `associate_by_embedding(..., index_backend=...)` 增加真实 backend smoke
- `VP-11` 给 `bench_scale.py` 增加小规模 backend compare smoke（flat/sqlite_vec/faiss）
- `VP-12` 清理 faiss SWIG warnings 对测试输出的影响，至少在测试里稳定可接受
- `VP-13` 更新 `docs/CHANGELOG.md` 的 vector/native backend 条目
- `VP-14` 更新 `docs/HANDOFF.md` 的安装与 smoke 命令
- `VP-15` 更新 `docs/superpowers/state/current-status.md` 的 vector 生产化状态
- `VP-16` 补 `.github/workflows/nightly.yml` 的 vector smoke lane
- `VP-17` 写 `ADR 0067`：v0.19 向量生产化决策
- `VP-18` 跑 Phase 65 回归并提交

## Phase 66 — 100k / 1M 规模证据（18 tasks）

- `SCX-1` 给 `bench_scale.py` 增加 `--backend all`，同 root 连跑 3 backend
- `SCX-2` 给 `bench_scale.py` 增加 `--seeded-prefix` 或隔离 root 策略，避免不同 backend 污染结果
- `SCX-3` 增加 100k synthetic run helper
- `SCX-4` 增加 1M synthetic run helper（仅 CLI，不进常规 CI）
- `SCX-5` archive `flat_python` 100k baseline
- `SCX-6` archive `sqlite_vec` 100k baseline
- `SCX-7` archive `faiss` 100k baseline
- `SCX-8` archive `flat_python` 1M baseline（若耗时可只 nightly/manual）
- `SCX-9` archive `sqlite_vec` 1M baseline
- `SCX-10` archive `faiss` 1M baseline
- `SCX-11` 生成 `docs/superpowers/state/2026-04-19-scale-bench-v2-report.md`
- `SCX-12` 在报告中比较 build_s / per_query_ms / qps / memory footprint
- `SCX-13` 给 tests 增加 archive schema 校验：backend / platform / python_version 必须存在
- `SCX-14` 给 nightly 增加 10k compare run，防性能回退
- `SCX-15` 给 release checklist 增加 native backend smoke
- `SCX-16` 更新 `docs/good_first_issues.md`，把“真 sqlite-vec 集成”替换为“100k/1M compare”
- `SCX-17` 写 `ADR 0068`：大规模 benchmark 证据与 baseline 策略
- `SCX-18` 跑 Phase 66 回归并提交

## Phase 67 — 联邦写路径（18 tasks）

- `FW-1` 设计 POST `/federation/v1/memories` contract
- `FW-2` 明确 bearer token、payload schema、error schema
- `FW-3` 实现 server 端 `do_POST` 路由
- `FW-4` 实现 payload validation：`scene_id` / `summary` / `owners` / `source`
- `FW-5` 实现 read-only default + 显式开关启用写路径
- `FW-6` 写入必须先创建 `event`
- `FW-7` 写入必须通过 `build_patch(operation='create_memory')`
- `FW-8` patch apply 后必须生成 snapshot / snapshot_entities
- `FW-9` 联邦写入后必须 invalidate retrieval cache
- `FW-10` 对 `exportable=false` / private owner 做拒绝策略
- `FW-11` 为 `FederationClient` 增加 `create_memory(...)`
- `FW-12` 为 `federation_fetcher` / integration 路径补写后读取验证
- `FW-13` 为 curl E2E 增加 POST happy path / 401 / 422 / 429
- `FW-14` 为 tests 增加 direct-table-write 禁止断言
- `FW-15` 更新 federation protocol v1.1 → v1.2 文档
- `FW-16` 更新 release docs / host docs 中的 curl 示例
- `FW-17` 写 `ADR 0069`：联邦写路径与安全边界
- `FW-18` 跑 Phase 67 回归并提交

## Phase 68 — 生产 HTTP E2E + 观测（16 tasks）

- `HE-1` 把联邦 server 的 curl smoke 写成脚本 `scripts/federation_e2e_smoke.sh`
- `HE-2` 给 `metrics_server.py` 增加 production curl 示例与 smoke
- `HE-3` dashboard / `/metrics` / federation 三路 smoke 统一成一套 production checklist
- `HE-4` 增加 server boot logs，明确 host/port/root/auth mode
- `HE-5` 给 federation server 增加 `/healthz` 或等价轻量健康检查
- `HE-6` 给 `FederationClient` error message 带 response body 摘要
- `HE-7` 为 curl E2E 增加 PII mask 断言
- `HE-8` 为 curl E2E 增加 rate limit 断言
- `HE-9` 为 curl E2E 增加 capabilities schema 断言
- `HE-10` 给 CI/nightly 接入 curl E2E smoke
- `HE-11` 更新 `docs/getting-started.md` 的 HTTP smoke 路径
- `HE-12` 更新 `docs/FAQ.md` 的 server 故障排查
- `HE-13` 更新 `docs/release/pypi_checklist.md` 的 HTTP smoke 项
- `HE-14` 更新 `docs/HANDOFF.md` 的生产环境测试命令
- `HE-15` 写 `ADR 0070`：production HTTP smoke as evidence
- `HE-16` 跑 Phase 68 回归并提交

## Phase 69 — 真 LLM 年运行（14 tasks）

- `LY-1` 给 `simulate_year.py` 增加真实 provider 参数与 usage report 汇总
- `LY-2` 给 `dream_cycle` 接真 LLM insight 生成（保留 mock fallback）
- `LY-3` 为 yearly run 加 `usage_json` / token / cost 累计字段
- `LY-4` 增加 `--monthly-report-dir`
- `LY-5` 增加 monthly cost summary artifact
- `LY-6` 增加 budget exhausted graceful stop / resume
- `LY-7` 给 real LLM run 增加 `--dry-run-provider-check`
- `LY-8` 给 tests 增加 usage schema / budget schema 验证
- `LY-9` 跑 7 天真实 provider smoke（小预算）
- `LY-10` 跑 30 天真实 provider sample（中预算）
- `LY-11` 跑 365 天真实 provider 年报告（大预算，manual）
- `LY-12` 写 `docs/superpowers/state/*year-run-llm-report.md`
- `LY-13` 写 `ADR 0071`：真实 LLM 年运行与预算审计
- `LY-14` 跑 Phase 69 回归并提交

## Phase 70 — 多 world / 多租户基线（14 tasks）

- `MW-1` 审计 `tenant_router` 当前行为与缺口
- `MW-2` 定义 world namespace / tenant namespace 的最小 contract
- `MW-3` 为 `world_service` 增加 namespace-aware query helper
- `MW-4` 为 `federation_service` 增加 world/tenant identity labels
- `MW-5` 为 retrieval path 增加 tenant isolation smoke
- `MW-6` 为 scripts 增加 `--tenant-id`
- `MW-7` 为 bootstrap / seed 路径增加 tenant root 约定
- `MW-8` 为 tests 增加 cross-tenant leakage negative cases
- `MW-9` 为 federation export 增加 namespace metadata
- `MW-10` 为 current-status / architecture docs 增加 tenant 模型说明
- `MW-11` 为 CLI 增加 tenant summary / tenant scene listing
- `MW-12` 设计跨 world migration contract（只设计，不大规模实现）
- `MW-13` 写 `ADR 0072`：multi-world / multi-tenant baseline
- `MW-14` 跑 Phase 70 回归并提交

## Phase 71 — EPIC（18 tasks）

- `EPIC-1` 汇总 Phase 65-70 测试增量与证据
- `EPIC-2` 写 `ADR 0073` synthesis
- `EPIC-3` 更新 `docs/CHANGELOG.md`
- `EPIC-4` 更新 `docs/release_notes_v0.19.0.md`
- `EPIC-5` 更新 `docs/HANDOFF.md`
- `EPIC-6` 更新 `docs/superpowers/state/current-status.md`
- `EPIC-7` 更新 `README.md` 的 v0.19 状态
- `EPIC-8` 更新 `docs/good_first_issues.md`
- `EPIC-9` 更新 `docs/release/pypi_checklist.md`
- `EPIC-10` 更新 benchmark / scenario / year-run 证据索引
- `EPIC-11` bump `pyproject.toml` version → `0.19.0`
- `EPIC-12` bump `src/we_together/cli.py` VERSION → `0.19.0`
- `EPIC-13` `python -m build --wheel`
- `EPIC-14` 隔离 venv 安装验证
- `EPIC-15` 全量 pytest / ruff / release_prep
- `EPIC-16` `git tag v0.19.0`
- `EPIC-17` 清理 pending / 更新 mega-plan 状态为 delivered
- `EPIC-18` 最终交接与下一轮候选（v0.20）

## 执行顺序

1. 先做 **Phase 65**，把真 backend 从“能跑”推进到“可发布、可集成、可归档”。
2. 再做 **Phase 66**，补 100k / 1M 证据，避免技术方向凭感觉推进。
3. 然后做 **Phase 67-68**，把 curl / HTTP / 联邦从 read-only demo 推到生产可验。
4. 最后做 **Phase 69-70**，再接真 LLM 年运行和多 world。

## 当前执行决策

本 session 直接开始：

- `VP-1` vector extra
- `VP-3..5` bench archive 化
- `VP-6..10` 真实 backend integration tests

完成后再推进 `VP-16..18`。
