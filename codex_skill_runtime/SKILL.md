---
name: we-together-runtime
description: "Use when the user is explicitly asking about the we-together runtime graph state: graph summary, invariants, invariant detail, self-describe, tenant state, or scene/memory/relation metadata in the we-together project. 中文强触发示例：we-together 图谱摘要、we-together 不变式、we-together 某条不变式、we-together 自描述。Do not use for continuing development phases, generic repository work, or unrelated social graph discussions."
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
version: "0.19.0"
---

> **语言**：用户说中文时，全程用中文。

# we-together-runtime

你只接管 `we-together` 的运行态元信息请求：

- 图谱摘要
- 不变式列表
- 某条不变式
- 自描述
- tenant / scene / memory / relation 元信息

首步规则：

1. 先读取 `references/local-runtime.md`
2. 再用其中声明的 MCP server 名称调用图谱工具
3. 图谱类请求优先走 MCP，不先扫源码

如果请求主要是继续开发或导入材料，不要接管，让更窄的子 skill 或 router 处理。

关键参考：

- `references/intent-examples.md`
