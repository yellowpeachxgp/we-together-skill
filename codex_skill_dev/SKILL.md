---
name: we-together-dev
description: "Use when the user is explicitly asking about we-together repository development work: current-status, HANDOFF, ADRs, invariants as engineering constraints, test baseline, continuing phases, or continuing implementation work in this repository. 中文强触发示例：we-together 当前状态、we-together 交接文档、继续 we-together 的 Phase、we-together 测试基线。Do not use for graph runtime summary, generic imports, or unrelated repositories."
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
version: "0.19.0"
---

> **语言**：用户说中文时，全程用中文。

# we-together-dev

你只接管 `we-together` 的开发态请求：

- 当前状态
- 交接文档
- ADR / 不变式的工程约束
- 测试基线
- 继续某个 Phase 或继续实现
- 明确的 `继续 Phase` 请求

首步规则：

1. 先读取 `references/local-runtime.md`
2. 直接以其中的 `repo_root` 为工作根
3. 先读状态文档，再读代码

如果请求是运行态摘要、图谱元信息或导入材料，不要接管，让更窄的子 skill 或 router 处理。

关键参考：

- `references/intent-examples.md`
