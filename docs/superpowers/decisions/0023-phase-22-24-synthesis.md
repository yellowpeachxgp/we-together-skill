# ADR 0023: Phase 22-24 综合 + 不变式扩展至 14 条

## 状态
Accepted — 2026-04-19

## 背景
Phase 22-24 让 we-together 从 v0.10.0 → v0.11.0，覆盖"联邦互操作 / 真集成 / 叙事深度"三条主干。

## 决策

### D1. 三域分层明确
- `federation/`（概念域）：external_person_refs + federation_fetcher + event_bus backends + canonical serializer
- `integration/`（测试域）：tests/integration/ 端到端真跑链
- `narrative/`（能力域）：narrative_service + perceived_memory + graph_analytics

### D2. 不变式扩展（在 ADR 0019 12 条基础上追加）

13. **联邦交互必须通过契约**：外部 person 引用走 external_person_refs → federation_fetcher → Backend Protocol，不得直接在 retrieval 里内嵌远端 HTTP 调用。

14. **真集成测试是门禁**：`tests/integration/` 任一失败视为 breaking。新增跨组件功能必须有对应 integration 测试。

## 版本锚点
- tag: `v0.11.0`
- 测试基线: **392 passed**
- schema 版本: 0012（migrations 0001-0012）
- ADR 总数: 23（0001-0023）
- benchmarks: 6

## 下一阶段候选（Phase 25+）
- 规模与真依赖（100 万 person / PG backend / imagehash / chromaprint）
- 真 HITL + RBAC 整合（branch_console 升级）
- i18n prompt（zh/en/ja）
- 真 Claude/OpenAI streaming
- PyPI 正式发布
