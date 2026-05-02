---
adr: 0062
title: Phase 60 — 反身能力（self_introspection）
status: Accepted
date: 2026-04-19
---

# ADR 0062: Phase 60 — 反身能力

## 状态
Accepted — 2026-04-19

## 背景
没有其他 memory 框架（Mem0/Letta/LangMem）能回答"**你是什么？你有哪些 ADR？你的不变式覆盖率如何？**"。这是 we-together 可以立的独特差异化——让 Skill 本身**能被 Claude 审查自己**。

## 决策

### D1. services/self_introspection
动态扫描仓库结构：
- `list_adrs()` 扫 `docs/superpowers/decisions/`，返回 `{adr_id, file, title, status}`
- `list_invariants()` 复用 `invariants.py`
- `check_invariant(id)` 返回单条 + 覆盖状态
- `list_services()` 扫 `src/we_together/services/`
- `list_migrations()` 扫 `db/migrations/`
- `list_scripts()` 扫 `scripts/`
- `list_plugins()` 复用 `plugin_registry.status()`
- `self_describe()` 聚合顶层概览（name / version / 三支柱 / 各项 total）

### D2. scripts/self_audit.py
一个 CLI 几种查看模式：
- 无参数 → `self_describe` 全景
- `--adrs` / `--invariants` / `--services` / `--migrations` / `--scripts` / `--plugins` / `--coverage` 各自查看

### D3. MCP 暴露
`mcp_adapter` 增加 3 个工具：
- `we_together_self_describe`
- `we_together_list_invariants`
- `we_together_check_invariant`

配合 `scripts/mcp_server.py` 的 dispatcher（由 v0.19 集成——当前 adapter 公布声明，dispatcher 路由可选）。

Claude Desktop 用户可以问：
> 用 we_together_self_describe 告诉我你自己有哪些能力

## 版本锚点
- tests: +15 (test_phase_60_rx.py)
- 文件: `services/self_introspection.py` / `scripts/self_audit.py` / `adapters/mcp_adapter.py`（+3 tools）

## 非目标（v0.19）
- MCP dispatcher 真路由 self_* tools（当前 tools 已声明；dispatcher 补接即可）
- ADR 互相引用图（"谁 superseded 谁"）
- 动态 service 调用关系图（静态 reference 计数）
- 全仓 AST 级别 import 分析

## 差异化论述

对比：
- **Mem0 / Letta / LangMem**：完全不暴露自描述能力
- **ChromaDB / Weaviate**：暴露 schema 但不暴露"我为什么这么设计"（ADR）
- **we-together**：唯一能回答"**你有哪 28 条不变式、每条挂在哪个测试里**"的 memory 框架

## 拒绝的备选
- 把 self_describe 塞进 retrieval_package：污染检索；专用 MCP 工具更清晰
- 外置 OpenAPI 文档生成：复杂；动态扫即可
- 把 ADR markdown 解析做成 AST：正则足够
