---
name: we-together-release
description: "Use when the user is explicitly asking about we-together release engineering, packaging, or publication readiness: package_skill, verify_skill_package, release_prep, release notes, CHANGELOG, or host smoke evidence. 中文强触发示例：we-together release、we-together 打包、we-together 发布说明、we-together CHANGELOG、we-together 自检。Do not use for generic graph/runtime questions, imports, or unrelated publishing workflows."
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
version: "0.19.0"
---

> **语言**：用户说中文时，全程用中文。

# we-together-release

你只接管 `we-together` 的 release / packaging 请求：

- `package_skill`
- `verify_skill_package`
- `skill_host_smoke`
- `release_prep`
- `CHANGELOG` / release notes / publish

首步规则：

1. 先读取 `references/local-runtime.md`
2. 直接以其中的 `repo_root` 为工作根
3. release 自检优先使用仓库现有脚本，而不是手拼检查项
4. 如果请求主要是交接文档、普通开发推进或运行态元信息，不要接管

关键参考：

- `references/intent-examples.md`
- `prompts/dev.md`
- `prompts/runtime.md`
