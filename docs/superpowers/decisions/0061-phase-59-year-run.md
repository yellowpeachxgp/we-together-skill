---
adr: 0061
title: Phase 59 — 年度真跑 + 月度归档
status: Accepted
date: 2026-04-19
---

# ADR 0061: Phase 59 — 年度真跑 + 月度归档

## 状态
Accepted — 2026-04-19

## 背景
tick 闭环（Phase 34）与 simulate_year 脚本（Phase 45）都已就位，但**从未真跑过 365 天**。vision "可持续演化"缺这最后的证据。

## 决策

### D1. run_year 重构
- 去掉 per-day `results` list（内存占用 & 无价值）
- 按 30 天切片聚合 `monthly` dict
- 返回：`total_snapshots_added / total_months / monthly / sanity / integrity`
- `archive_dir` 参数：传入则归档到 `<dir>/year_run_<ts>.json`

### D2. CLI 加 `--archive-monthly`
- 默认不归档
- `--archive-monthly` → 写入 `<root>/benchmarks/year_runs/`

### D3. 首份真归档
`benchmarks/year_runs/year_run_2026-04-18T21-20-54Z.json` 已入仓库。365 天真跑，healthy=True，integrity=True。
这是**可复现的历史证据**：任何人拉代码都能对比。

### D4. 报告文档
`docs/superpowers/state/2026-04-19-year-run-report.md` 描述首次真跑的观察、复现步骤、下一步。

## 不变式
本 ADR 不新增不变式；但强化不变式 #20（tick 可回滚）和 #24（graph_clock 优先）——365 天真跑证明二者稳定。

## 版本锚点
- tests: +8 (test_phase_59_sy.py)
- 首份归档: `benchmarks/year_runs/year_run_*.json`
- docs: `year-run-report.md`

## 非目标（v0.19）
- 真 LLM 跑 + 成本采样
- 50 人规模跑 365 天（当前 seed_society_c 只 2 人）
- 并发 scene / 多 world
- 月度指标时序图

## 拒绝的备选
- 每天一个月度 snapshot 文件：文件爆炸
- 去掉 monthly 只返 final：失去时间维度
