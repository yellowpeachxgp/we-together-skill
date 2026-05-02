---
adr: 0064
title: Phase 62 — Exemplar Scenarios 真跑归档
status: Accepted
date: 2026-04-19
---

# ADR 0064: Phase 62 — Exemplar Scenarios

## 状态
Accepted — 2026-04-19

## 背景
`docs/tutorials/family_graph.md` 写了家庭场景的教程，但**没有 code-driven 的真跑归档**。Phase 62 补：3 个 scenario 端到端跑通 + 归档证据。

## 决策

### D1. scripts/scenario_runner.py
3 个内置 scenario：
- `family`：4 人家庭 + 3 段家庭叙述
- `work`：6 人工作团队 + 3 段职场叙述
- `book_club`：5 人读书会 + 3 段讨论

每个 scenario run：
1. bootstrap 独立 root
2. seed persons + scene + narrations
3. 写 memory + event
4. 归档 JSON 到 `examples/scenarios/<name>/run_<ts>.json`

### D2. `--scenario all --archive` 一键全跑
3 个 scenario 真跑过，归档文件入仓库。

## 版本锚点
- tests: +4 (test_phase_62_63.py 前 4 条)
- 归档: `examples/scenarios/{family,work,book_club}/run_*.json`

## 非目标
- scenario 真跑 LLM（需 key）
- scenario 接入 multi_agent_dialogue（留 v0.19）
