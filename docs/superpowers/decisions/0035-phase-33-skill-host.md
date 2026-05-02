---
adr: 0035
title: Phase 33 — 真 Skill 宿主落地（MCP/OpenAI/Claude）
status: Accepted
date: 2026-04-19
---

# ADR 0035: Phase 33 — 真 Skill 宿主落地

## 状态
Accepted — 2026-04-19

## 背景
此前 `scripts/mcp_server.py` 仅实现 `initialize + tools/list + tools/call`；OpenAI Assistants 适配器没有 demo；Claude Skills 打包只有 skill_packager 函数，没有端到端 verify。这些是 B 支柱"通用型 Skill"的实体证据缺口。

## 决策

### D1. MCP server 补齐 resources + prompts
- `resources/list` + `resources/read` 暴露 `we-together://graph/summary` 与 `we-together://schema/version`
- `prompts/list` + `prompts/get` 暴露 `we_together_scene_reply`
- tools 数量 2 → 6（+ scene_list / snapshot_list / import_narration / proactive_scan）

### D2. Skill manifest + verify loop
- `skill_packager.pack_skill` 已有；补 `scripts/verify_skill_package.py`
- verify：解包 zip → 校验 manifest 必填 → 输出 smoke 报告

### D3. OpenAI Assistants demo
- `scripts/demo_openai_assistant.py`：把 MCP tools 翻译为 OpenAI function schema
- mock 模式本地跑；真跑需 `WE_TOGETHER_LLM_PROVIDER=openai_compat` + key

## 版本锚点
- tests: +9（test_phase_33_skill_host.py 12 tests total）
- 文件: `scripts/mcp_server.py` / `runtime/adapters/mcp_adapter.py` / `scripts/verify_skill_package.py` / `scripts/demo_openai_assistant.py`

## 非目标（留后续阶段）
- 真 Claude Skills marketplace 上架（需要外部审批）
- MCP SSE transport（当前仅 stdio）
- OpenAI Assistants 真跑 + streaming tools（需 key + 预算）
- 飞书机器人真部署（需企业账号）

## 拒绝的备选
- 自写 MCP SDK：协议 spec 已稳定，直接 hand-code JSON-RPC 更轻
- 把 we-together 绑死 Claude SDK：违反"通用型 Skill"B 支柱
