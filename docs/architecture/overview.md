# Architecture Overview

> 当前架构基线：v0.20.1。更面向使用者的说明见 [Wiki 架构总览](../wiki/architecture.md)。

## 一句话架构

we-together 是一个本地优先的 Skill runtime：宿主入口接收用户请求，runtime 从 SQLite 社会/世界图谱构建 scene-grounded retrieval package，LLM 或 mock 生成回复，随后系统按 event -> patch -> snapshot 链路演化图谱。

## 层级

```text
Host / User
  ├─ CLI: src/we_together/cli.py -> scripts/*.py
  ├─ MCP: scripts/mcp_server.py
  ├─ WebUI: webui/ + scripts/webui_host.py
  └─ Native skill family: ~/.codex/skills/we-together*

Runtime
  ├─ skill_runtime.py: SkillRequest / SkillResponse
  ├─ prompt_composer.py
  ├─ adapters/: claude / openai / mcp / feishu / langchain / coze
  └─ sqlite_retrieval.py: scene-grounded retrieval package

Services
  ├─ chat_service.run_turn
  ├─ ingestion / fusion / candidate / branch services
  ├─ patch_service / patch_applier / snapshot_service
  ├─ drift / decay / forgetting / merge / unmerge
  ├─ world_service / autonomous_agent / dream_cycle
  └─ observability / federation / plugin registry

Storage
  ├─ SQLite migrations 0001..0021
  ├─ default tenant: <root>/db/main.sqlite3
  └─ named tenant: <root>/tenants/<tenant_id>/db/main.sqlite3
```

## 关键契约

1. **Skill-first**：运行时逻辑不绑死某个宿主。
2. **Event-first**：演化先写 event，再推理 patch，再改图谱。
3. **Patch-only graph writes**：结构性写入走 patch/service 层。
4. **Snapshot rollback**：对话、tick、演化路径必须保留可回滚证据。
5. **Local-first token ownership**：浏览器不是默认 provider token 持有者。
6. **Tenant routing**：不同 tenant 使用独立 DB root，runtime 语义保持一致。

## 主对话链

```text
scene_id + input
  -> build_runtime_retrieval_package_from_db()
  -> build_skill_request()
  -> adapter.invoke()
  -> LLM provider or mock
  -> record_dialogue_event()
  -> infer_dialogue_patches()
  -> apply_patch_record()
  -> event_id + snapshot_id + applied_patch_count
```

对应代码入口：

- `src/we_together/services/chat_service.py`
- `src/we_together/runtime/sqlite_retrieval.py`
- `src/we_together/runtime/skill_runtime.py`
- `src/we_together/services/dialogue_service.py`
- `src/we_together/services/patch_applier.py`

## WebUI 架构

WebUI 现在是本地 skill runtime 的界面。默认开发启动：

```bash
we-together webui --root <root>
```

这会启动：

- `scripts/webui_host.py` 本地 bridge
- Vite WebUI
- `/api/*` proxy 到 bridge

默认 API：

- `GET /api/runtime/status`
- `GET /api/scenes`
- `GET /api/summary`
- `POST /api/chat/run-turn`

`POST /api/chat/run-turn` 最终调用 `chat_service.run_turn()`。WebUI token 只用于高级远程 API 模式。

## 当前代码事实

来自 `scripts/self_audit.py`：

- version: `0.20.1`
- ADR: 73
- invariants: 28 / covered 28
- migrations: 21
- services: 84
- scripts: 76

来自 `scripts/invariants_check.py summary`：

- `coverage_ratio`: `1.0`
- `uncovered`: `0`

## 进一步阅读

- [Wiki 架构总览](../wiki/architecture.md)
- [能力边界](../wiki/capabilities.md)
- [交互流程](../wiki/interaction-flows.md)
- [当前状态](../superpowers/state/current-status.md)
- [HANDOFF](../HANDOFF.md)
