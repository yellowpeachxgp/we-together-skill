---
name: we-together-ingest
description: "Use when the user is explicitly asking to bootstrap we-together data roots or import material into the we-together project: bootstrap, narration import, text import, email import, file import, directory import, or auto import. 中文强触发示例：we-together 导入材料、we-together bootstrap、we-together 导入口述文本。Do not use for graph summary, invariant queries, or continuing engineering phases."
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
version: "0.20.1"
---

> **语言**：用户说中文时，全程用中文。

# we-together-ingest

你只接管 `we-together` 的导入态请求：

- bootstrap
- narration / text / email / file / directory / auto import
- 初始化图谱数据根

首步规则：

1. 先读取 `references/local-runtime.md`
2. 在其中的 `repo_root` 下执行仓库脚本
3. 导入后优先返回导入结果与图谱摘要

如果请求主要是状态查询、交接文档、图谱元信息或继续开发，不要接管，让更窄的子 skill 或 router 处理。

关键参考：

- `references/intent-examples.md`
