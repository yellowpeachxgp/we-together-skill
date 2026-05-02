---
adr: 0041
title: Phase 39 — Tick 真运行 + 归档
status: Accepted
date: 2026-04-19
---

# ADR 0041: Phase 39 — Tick 真运行 + 归档

## 状态
Accepted — 2026-04-19

## 背景
Phase 34（v0.14）落地 tick 编排骨架，但：
- simulate_week 脚本存在 ≠ 真跑过
- 没有归档 benchmark，下次回归无参考
- tick 的 snapshot 实际上被 try/except 吞了（Phase 38 修复）
- LLM 成本模型没写
- 调度（cron / NATS）无示例

Phase 39 把"能跑"升级为"**真跑 + 真归档**"。

## 决策

### D1. simulate_week 真跑 + 归档
- `scripts/simulate_week.py` 新增 `--archive` 开关
- 归档到 `benchmarks/tick_runs/<ISO ts>.json`
- 首份 baseline `benchmarks/tick_runs/2026-04-18T19-37-40Z.json`（7 tick, budget=0, seed_society_c）

### D2. TickCostTracker 服务
- `services/tick_cost_tracker.py`
- `track(provider, prompt_tokens, completion_tokens)` 精确
- `track_estimated(provider, text_in, text_out)` 粗估（chars/4）
- `summary()` 返回总 calls/tokens + by_provider 分档
- **不硬编单价**；真成本需乘 provider 价目，留给宿主层

### D3. rollback_tick CLI
- `scripts/rollback_tick.py --snapshot snap_tick_3_xxx`
- 委派到 `time_simulator.rollback_to_tick`（复用 snapshot_service）
- 闭合不变式 #20 的消费路径

### D4. 调度示例文档
- `docs/tick-scheduling.md`
- crontab / k8s CronJob / NATS trigger 三种示例
- 不做真 cron daemon（维持"宿主调度"立场，见 ADR 0036）

### D5. 30-tick 稳定性测试
- `test_long_run_30_ticks_stable`：seed + 30 tick + `evaluate` healthy
- 作为回归 baseline，下次改 tick 引擎时必须保持 healthy

## 版本锚点
- tests: +10 (test_phase_39_ct.py)
- 文件: `services/tick_cost_tracker.py` / `scripts/rollback_tick.py` / `docs/tick-scheduling.md`
- 归档: `benchmarks/tick_runs/2026-04-18T19-37-40Z.json`
- simulate_week.py: `build_report` + `archive` 拆分，可被测试直接调用

## 非目标（留 v0.16）
- 真 Anthropic/OpenAI key 跑 simulate_week（需 budget）
- cost tracker 乘上真单价（依宿主）
- tick metrics → Prometheus 持久化 exporter（当前仅 Tracker 内存）

## 拒绝的备选
- 引入 APScheduler：重；宿主 cron 更标准
- 把 tick 持久化到新 migration 表：当前 snapshot_id LIKE 'snap_tick_%' 查询已够用
