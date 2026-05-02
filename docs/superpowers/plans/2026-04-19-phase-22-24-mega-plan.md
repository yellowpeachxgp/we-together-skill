# Phase 22-24 Mega Plan 归档（2026-04-19 第四轮无人值守）

## 目标
v0.10.0 (349 passed, 19 ADR) → v0.11.0：联邦 / 真集成 / 叙事三条主干。

## 达成情况

| Phase | 主题 | 切片 | 关键产出 | 测试增量 |
|---|---|---|---|---|
| 22 | 联邦与互操作 | FE-5/6/7 + IO-1/2/3 | federation_fetcher / NATS+Redis stub / hot_reload / migration importer / canonical serializer / RFC | +22 |
| 23 | 真集成 + 生产级 | IT-1/2/3/5/6/7 | integration/ 真跑链 / agent_runner tool_use loop / streaming / wheel 验证 / CI workflow / pre-commit | +12 |
| 24 | 图谱叙事深度 | ND-1/2/3/5 | migration 0011/0012 / narrative_service / perceived_memory / graph_analytics / associative_recall / narrate+analyze CLI | +9 |

**总增量**：349 → 392 passed（+43），commits ≈ 8。

## 新增模块 / 文件

- `src/we_together/services/`: federation_fetcher, hot_reload, narrative_service, perceived_memory_service, graph_analytics, associative_recall, graph_serializer
- `src/we_together/importers/migration_importer`（CSV / Notion / Signal）
- `src/we_together/runtime/`: agent_runner, streaming
- `tests/integration/test_full_flow.py`
- `db/migrations/0011_narrative_arcs.sql`, `0012_perceived_memory.sql`
- `scripts/`: migrate / graph_io / narrate / analyze / build_wheel
- `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `MANIFEST.in`（已有，强化）
- `docs/superpowers/decisions/0020-0023.md`
- `docs/superpowers/specs/2026-04-19-federation-protocol.md`
- `docs/federation/bus_backends.md`

## 不在本轮范围（留给 Phase 25+）

- 真 Claude/OpenAI streaming adapter
- PyPI 正式上传（只准备了 checklist + 本地 wheel 验证）
- 真 NATS drain / Redis Stream consumer group
- 图谱级 embedding（associative_recall 是 LLM stub）
- branch_console fastapi 升级
- HITL + RBAC 整合
- 10 万/百万 person 压测

## 下一轮候选（Phase 25 规模与真依赖 + Phase 26 多语言+HITL）

详见 `docs/superpowers/decisions/0023-phase-22-24-synthesis.md` 末尾。
