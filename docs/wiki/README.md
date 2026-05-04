# we-together Wiki

> 面向使用者、继任开发者和宿主集成者的稳定入口。这里不追逐每个 phase 的过程细节，只保留当前能帮助你理解和使用系统的事实。

## 当前基线

| 项 | 当前事实 |
|---|---|
| 版本 | `we-together 0.20.1` |
| 定位 | Skill-first 的社会 + 世界图谱运行时 |
| 存储 | 本地 SQLite + 文件系统目录，默认 `<root>/db/main.sqlite3` |
| 多租户 | `default` 使用 `<root>/db/main.sqlite3`，其他 tenant 使用 `<root>/tenants/<tenant_id>/db/main.sqlite3` |
| 工程证据 | 73 ADR、28 条不变式、21 migrations、84 services、76 scripts |
| 默认 LLM | `mock`，不需要 API key 也能跑通链路 |
| WebUI 默认通道 | Local skill bridge，不要求浏览器填写 WebUI token |
| 严格发布门禁 | `.venv/bin/python scripts/release_strict_e2e.py --profile strict` |

代码事实来源：

- `scripts/self_audit.py`
- `scripts/invariants_check.py summary`
- `.venv/bin/we-together --help`
- `docs/HANDOFF.md`
- `docs/superpowers/state/current-status.md`

## 推荐阅读路径

1. [架构总览](architecture.md)
   先理解系统怎么分层、图谱如何演化、WebUI 为什么不该持有 provider token。

2. [使用方法](usage.md)
   从安装、bootstrap、seed/import、CLI、WebUI、Codex skill family 到验证命令。

3. [能力边界](capabilities.md)
   分清已经能稳定做什么、哪些能力依赖真实 provider、哪些还是高级/后续模式。

4. [交互流程](interaction-flows.md)
   用流程图理解 CLI、WebUI、Codex/MCP、导入、operator review、tick 和多租户。

5. [最终 Skill 产品定义与开发 Prompt](../superpowers/specs/2026-05-03-final-skill-product-prompt.md)
   用于理解 we-together 最终应产出的 skill 产品形态、体验标准、开源价值和下一阶段开发约束。

## 一句话理解

we-together 不是把 memory 做成一个向量缓存，而是把 Person、Relation、Scene、Event、Memory、State、Object、Place、Project 等对象放进一个可审计、可回滚、可演化的本地图谱里。LLM 只是运行时的一部分，真正的产品内核是：

```text
输入或导入材料
  -> event / evidence / candidate
  -> retrieval_package
  -> SkillRequest
  -> LLM 或 mock response
  -> dialogue_event
  -> inferred patches
  -> graph state + snapshot
```

## 现在最重要的使用提醒

- 新 root 跑完 `bootstrap` 后，数据库存在但通常没有可对话 scene。
- 想立刻体验完整链路，请先跑 `seed-demo`，或导入材料并创建 scene。
- WebUI 的默认对话不需要 WebUI token。浏览器请求 `/api/chat/run-turn`，Vite 代理到本地 `scripts/webui_host.py`，bridge 再调用 `chat_service.run_turn()`。
- Provider token 属于 CLI/本地运行环境。只有高级远程 API 模式才需要在 WebUI 里配置 token。
- WebUI 默认不静默使用 demo 数据。视觉开发 demo 需要显式设置 `localStorage.we_together_demo_mode=1` 或 URL `?demo=1`。
- 新启动的 MCP stdio 已通过 strict gate；如果当前 Codex 会话挂载的是旧 MCP 进程，`snapshot_list` 可能仍需重启 MCP 后复测。

## 相关入口

- [文档首页](../index.md)
- [5 分钟 Quickstart](../quickstart.md)
- [Getting Started](../getting-started.md)
- [架构 overview](../architecture/overview.md)
- [Codex 接入指南](../hosts/codex.md)
- [当前状态](../superpowers/state/current-status.md)
- [交接文档](../HANDOFF.md)
