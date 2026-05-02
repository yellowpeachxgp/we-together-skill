---
adr: 0030
title: Phase 30 — Proactive Graph
status: Accepted
date: 2026-04-19
---

# ADR 0030: Phase 30 — 主动图谱

## 状态
Accepted — 2026-04-19

## 背景
之前所有图谱演化都"**被动**"——必须有用户输入才会变。Phase 30 让图谱长出**主动神经元**：周期性扫触发器（纪念日/沉默/冲突）→ 生成 intent → 经预算 + 偏好门控 → 执行写 event。

## 决策

### D1. Trigger 抽象（PG-1）
- `services/proactive_agent.py: Trigger(name, metadata)`
- 三类触发器：
  - `scan_anniversary_triggers(db)`：30 天前 / 1 年前的高 relevance memory
  - `scan_silence_triggers(db)`：N 天无 event 的 person
  - 冲突触发由 contradiction_detector 复用（Phase 31）
- `scan_all_triggers(db)`：综合三路返回

### D2. ProactiveIntent 与执行（PG-3）
- `ProactiveIntent(action, target_id, text, confidence, source_trigger, metadata)`
- `generate_intent(trigger, llm_client)` → LLM JSON 输出 `{action, text, confidence}`
- `execute_intent(db, intent)` → 写 `events` 表 (`event_type=proactive_intent_event`, `source_type=proactive_agent`)
- `proactive_scan(db, daily_budget, llm_client)` 一键串：scan → generate → check_budget → execute

### D3. 预算（PG-3c）
- `check_budget(db, daily_budget)` 数当日 `proactive_intent_event` 数量，返回剩余配额
- 默认 `daily_budget=3`，避免主动消息洪水

### D4. 偏好（PG-4）
- migration `0014_proactive_prefs.sql`：`proactive_prefs(person_id, trigger_name, mode, allowed)`
- API: `set_mute(db, person_id, mute)` / `set_consent(db, person_id, trigger, allowed)` / `is_allowed(db, person_id, trigger)`
- mute 优先于 consent；未配置默认允许

## 不变式增量
（参见 ADR 0033 第 18 条：主动写入必须经预算 + 偏好门控）

## 版本锚点
- tests: +5 (proactive_prefs / scan / scan_writes_event / check_budget)
- migration: 0014
- 主动事件复用 events 表（不新建）

## 拒绝的备选
- 独立 `proactive_events` 表：违反"事件优先"统一性
- 真 cron daemon：v0.13 不内置，留给宿主调度（cron / k8s job / nats trigger）
