# Phase 8-12 Mega Plan 归档（2026-04-18 一次性无人值守推进）

## 目标

在一次连续无人值守工作流中，把 we-together-skill 从 216 passed / Phase 7 末尾推进到 Phase 12 末尾（281 passed，覆盖五个大目标：图谱活化 / 宿主生态 / 真实世界数据化 / 联邦与协同 / 生产化硬化）。

## 达成情况

| Phase | 主题 | 切片数 | 关键产出 | 测试增量 |
|---|---|---|---|---|
| 8 | 图谱活化（Neural Mesh） | NM-1..NM-6 | multi_scene_activation / memory cluster+condense / persona_drift / pair interactions / cross_scene_echoes / cold_memories | +18 |
| 9 | 宿主生态 | HE-1..HE-7 | SkillRequest.tools / agent_loop / skill 打包 / 飞书/LangChain/Coze/MCP 四 adapter | +20 |
| 10 | 真实世界数据化 | RW-1..RW-6 | iMessage / 微信 db / MBOX / VLM image / 社交 JSON / evidence 去重 | +6 |
| 11 | 联邦与协同 | FE-1..FE-4 | external_person_refs migration 0008 / jsonl 事件总线 / 裁决 UI / 多租户路由 | +8 |
| 12 | 生产化硬化 | HD-1..HD-9 | logger+trace / metrics / config toml / errors 层级 / schema_version / patch_batch / cache_warmer / bench_large | +13 |

## 新增文件（摘要）

- `db/migrations/0007_cold_memories.sql`
- `db/migrations/0008_external_person_refs.sql`
- `src/we_together/runtime/multi_scene_activation.py`
- `src/we_together/runtime/adapters/{feishu,langchain,coze,mcp}_adapter.py`
- `src/we_together/services/{memory_cluster,memory_condenser,persona_drift,relation_conflict,memory_archive,federation,event_bus,tenant_router,patch_batch,cache_warmer}_service.py` 等
- `src/we_together/importers/{imessage,wechat_db,mbox,image,social}_importer.py`
- `src/we_together/llm/providers/vision.py`
- `src/we_together/observability/{logger,metrics}.py`
- `src/we_together/config/loader.py`
- `src/we_together/errors.py`
- `src/we_together/db/schema_version.py`
- `src/we_together/packaging/skill_packager.py`
- `scripts/{condense_memories,cold_memory,agent_chat,package_skill,branch_console,bench_large,metrics_server}.py`
- `docs/superpowers/decisions/000{4,5,6,7,8}-phase-*.md`

## 不在本轮范围（留给后续）

- 真正事务化的 patch_batch（需 refactor apply_patch_record 签名）
- 跨机事件总线（NATS/Redis Stream）
- RBAC / 多租户权限隔离
- 日志/metrics 可插拔 sink
- fastapi+htmx 版本裁决 UI（当前是 stdlib http.server）
