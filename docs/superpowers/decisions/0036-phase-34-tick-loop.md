---
adr: 0036
title: Phase 34 — 持续演化 Tick 闭环
status: Accepted
date: 2026-04-19
---

# ADR 0036: Phase 34 — 持续演化 Tick 闭环

## 状态
Accepted — 2026-04-19

## 背景
此前 `state_decay / relation_drift / proactive_scan / self_activation` 各自独立 service，需要外部手动触发。没有统一的"图谱时钟"把它们编排到一次 tick 里；更没有"跑一周 tick 看图谱是否 believable"的闭环。这是 C 支柱"可持续演化的数字赛博生态圈"最核心的缺口。

## 决策

### D1. TimeSimulator 编排层
- `services/time_simulator.py`
- `TickResult` 记录一次 tick 的 decay/drift/proactive/self_activation 结果 + 可选 snapshot_id
- `TickBudget` 控 LLM 调用数 / proactive 日配额 / drift/decay limit
- `run_tick(db, tick_index, budget, llm_client, do_*)` 单次编排
- `simulate(db, ticks, budget, llm_client)` 连续 N 次

### D2. 默认行为：tick 后自动 snapshot
每次 `run_tick` 结束调 `_make_snapshot_after_tick`，在 `snapshots` 表落 `snap_tick_{i}_{ts}`。
这让**任意 tick 结束点都有一个 commit 边界**，可通过 `rollback_to_tick(db, snapshot_id)` 回滚。

### D3. hook 机制
- `register_before_hook(fn(idx, db))` / `register_after_hook(fn(result, db))`
- 供 observability sink（`llm_hooks.sink`）接入做 metrics

### D4. 预算与优雅退化
- LLM 预算耗尽时，`proactive_scan` / `self_activation` 被跳过并标 `budget_exhausted=True`，**不抛异常**
- 非 LLM 步骤（decay/drift）始终执行

### D5. 合理性评估
- `services/tick_sanity.py`：
  - `check_growth(db, ticks, max_memory_per_tick, max_event_per_tick)`
  - `check_anomalies(db)`：low confidence / orphan memory / duplicate event summary
  - `evaluate(db, ticks)` 综合报告 + `healthy: bool`
- 这是"跑完一周看看是否炸"的第一道拦截

### D6. CLI 入口
- `scripts/simulate_week.py --root . --ticks 7 --budget 30` 输出 JSON 报告

## 不变式（新，v0.14.0 第 20 条）
**#20**：tick 写入必须能在无人工干预下被 snapshot 回滚至任一时间点（闭环可逆）。

## 版本锚点
- tests: +11 (test_phase_34_tick.py)
- 文件: `services/time_simulator.py` / `services/tick_sanity.py` / `scripts/simulate_week.py`

## 拒绝的备选
- 真 cron daemon：违反"宿主调度"立场，让宿主用 crontab/k8s job 调 simulate_week
- tick 内自动触发写 patch：已有 proactive_agent 走 events + 预算路径，不再在 tick 里直接写 patch
- 跳过 snapshot：违反不变式 #20；rollback 没有边界可用

## 留给后续
- `tick_summary_view`：读 N 次 tick 的 delta，在面板呈现
- `tick trigger from NATS`：让事件驱动一次 tick（而非日历驱动）
- "合理性评估"增加 LLM-based plausibility judge
