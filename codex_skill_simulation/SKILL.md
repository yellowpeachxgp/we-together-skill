---
name: we-together-simulation
description: "Use when the user is explicitly asking about we-together simulation, projection, or long-run evolution workflows: what-if, simulate_week/year, dream_cycle, tick replay, or future-state analysis. 中文强触发示例：we-together 模拟、we-together what-if、we-together simulate_year、we-together dream_cycle。Do not use for generic project status, plain graph summary, or unrelated forecasting tasks."
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
version: "0.20.1"
---

> **语言**：用户说中文时，全程用中文。

# we-together-simulation

你只接管 `we-together` 的模拟 / 推演请求：

- `what-if`
- `simulate_week` / `simulate_year`
- `dream_cycle`
- tick / rollback / projection
- future-state 分析与产物

首步规则：

1. 先读取 `references/local-runtime.md`
2. 直接以其中的 `repo_root` 为工作根
3. 优先使用现有 CLI：`scripts/what_if.py` / `simulate.py` / `simulate_week.py` / `simulate_year.py` / `dream_cycle.py`
4. 如果请求变成仓库状态摘要或普通实现推进，不要接管

关键参考：

- `references/intent-examples.md`
- `prompts/runtime.md`
- `prompts/dev.md`
