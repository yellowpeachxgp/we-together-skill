---
adr: 0066
title: Phase 58-64 综合 + 不变式扩展至 30 条
status: Accepted
date: 2026-04-19
---

# ADR 0066: Phase 58-64 综合 + 不变式扩展至 30 条

## 状态
Accepted — 2026-04-19

## 背景
v0.17 所有"代码功能"基本到位（9.8/9.8/9.5）。Phase 58-64 做的是**相反方向**的工作：
- **不加新 schema**
- **不加新 feature**
- **只做纵深验证 + 反身能力 + 证据累积**

这是项目第一次**往回补证据**，把"声明"变"事实"。

## 决策

### D1. 不变式 → 测试 强制映射（ADR 0060）
- `invariants.py` 30 条不变式注册表
- 每条 >= 1 个 test_refs 挂钩
- meta-tests 强制真实存在
- 不变式 **#29** 落地

### D2. 365 天真跑（ADR 0061）
- `benchmarks/year_runs/year_run_*.json` 首份真归档
- 365 day healthy=True integrity=True
- `simulate_year --archive-monthly`

### D3. 反身能力（ADR 0062）
- `services/self_introspection` 让 we-together 能描述自己
- MCP 9 tools（+3 self-*）
- `scripts/self_audit.py` 综合自审
- 独特差异化：其他 memory 框架不做这事

### D4. 规模化真压测（ADR 0063）
- 10k: QPS 65.6 / per-query 15.23ms
- 50k: QPS 12.7 / per-query 78.88ms
- `benchmarks/scale/bench_*.json` 归档

### D5. Exemplar Scenarios（ADR 0064）
- 3 个真跑场景：family / work / book_club
- `examples/scenarios/*/run_*.json` 归档证据

### D6. 纸面工程化根除（ADR 0065）
- 所有 ADR 必须有 status frontmatter
- 不变式 **#30** 落地

### D7. 不变式累计 → 30 条
ADR 0059 已有 28 条。v0.18 新增：

**#29**：纸面不变式禁止——每条不变式必须有 >= 1 个 test_refs 且真实存在。

**#30**：ADR 必须声明 status（Active / Accepted / Superseded / Archived）；不允许僵尸 ADR。

### D8. 三支柱 v0.18 达成度
- **A 严格工程化**：9.8 → **9.95**（不变式 #29/#30 + 年度真跑 + 反身能力；几乎封顶）
- **B 通用型 Skill**：9.8 → **9.8**（维持；真上架留外部）
- **C 数字赛博生态圈**：9.5 → **9.7**（365 天证据 + 3 个 exemplar scenarios + 50k 规模验证）

## 版本锚点
- tag: `v0.18.0`
- 测试基线: **690 passed + 2 skipped**（+52 over v0.17 的 638）
- ADR 总数: **66**（0001-0066）
- 不变式: **30**
- migration 数: **21**（未变——本版本不加新 schema 是**有意为之**）
- 新归档：`benchmarks/year_runs/` + `benchmarks/scale/` + `examples/scenarios/`
- 新 service 模块: `invariants` / `services/self_introspection`
- 新 CLI: `invariants_check` / `self_audit` / `scenario_runner`

## 证据清单（可审计）
- ✅ `benchmarks/year_runs/year_run_2026-04-18T21-20-54Z.json`：365 天真跑
- ✅ `benchmarks/scale/bench_10k_*.json` / `bench_50k_*.json`：规模化压测
- ✅ `examples/scenarios/{family,work,book_club}/run_*.json`：3 场景真跑
- ✅ `docs/superpowers/state/2026-04-19-invariants-coverage.md`：30 条 → 30 条测试
- ✅ `docs/superpowers/state/2026-04-19-year-run-report.md`：年度报告
- ✅ `docs/superpowers/state/2026-04-19-scale-bench-report.md`：压测报告

## 下一阶段候选（Phase 65+，v0.19）
- 真 sqlite-vec / FAISS 集成（真接入不只 stub）
- 真 LLM 跑 simulate_year + 成本采样
- mkdocs 真建站 + GitHub Pages
- Claude Skills 真提交
- PyPI 正式发布
- 多 world / 多租户
- narrative_v2 深度升级
- 性能回归 CI baseline 对比

## 对外释出
建议：
- v0.18.0 标签 + GitHub Release
- "从代码到可验证的生态圈" — 营销 angle
- 社区推广：vs Mem0/Letta/LangMem 对比文档 + 反身能力差异化
