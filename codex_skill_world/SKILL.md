---
name: we-together-world
description: "Use when the user is explicitly asking about we-together tenant/world runtime or world-model operations: tenant state, active world, world objects/places/projects, world CLI, or world isolation boundaries. 中文强触发示例：we-together tenant 状态、we-together world 摘要、we-together 世界对象、we-together place/project。Do not use for generic project status, generic imports, or unrelated worldbuilding."
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
version: "0.20.0"
---

> **语言**：用户说中文时，全程用中文。

# we-together-world

你只接管 `we-together` 的 tenant / world 语义请求：

- tenant 状态
- active world / 世界快照
- object / place / project 元信息
- `world_cli` / world-aware 边界
- world isolation / tenant isolation 相关实现

首步规则：

1. 先读取 `references/local-runtime.md`
2. 直接以其中的 `repo_root` 为工作根
3. world 运行态优先查 `scripts/world_cli.py` 与 `src/we_together/services/world_service.py`
4. 如果请求转成 Phase / ADR / 基线推进，再回到开发态文档

如果请求主要是交接文档、总览摘要或 release，不要接管。

关键参考：

- `references/intent-examples.md`
- `prompts/runtime.md`
- `prompts/dev.md`
