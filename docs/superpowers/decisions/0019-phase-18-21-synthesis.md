# ADR 0019: Phase 18-21 综合 + 不变式扩展至 12 条

## 状态

Accepted — 2026-04-19

## 背景

Phase 18-21 让 we-together-skill 从 v0.9.0 迈向 v0.10.0：真实宿主接入、多模态、模拟完整版、eval 扩展。本 ADR 聚合这一轮的共同抽象与新增不变式。

## 决策

### D1. `simulation/` 与 `services/` 的责任分工

- `services/` 持有会改图谱的动作（retire_person、drift、decay 等）
- `simulation/` 持有纯推演（what_if、conflict_predictor、scene_scripter、era_evolution），默认不改图谱；`simulate_era` 是例外，它主动调用 services 触发演化

### D2. 新增不变式（在 ADR 0014 10 条基础上追加）

11. **所有宿主 adapter 的 real-run 必须能在 mock LLM 下跑完端到端链**（Phase 18 MCP / 飞书测试全走 mock，零网络）
12. **benchmark 文件是合约**：修改要更新 ADR + CHANGELOG；`benchmarks/*.json` 任一字段删减视为 breaking

### D3. "推演 vs 演化" 的分层原则

- `simulation/` 输出是 `{predictions, scripts, hypothetical_branches}`，**不落库**
- 如果要把推演结果变成实际演化，必须走 `services/` 的 patch/event 路径
- 这条分层让 Phase 22 未来的"Hypothetical mode"能干净接入

## 版本锚点

- tag: `v0.10.0`
- 测试基线: **349 passed**
- schema 版本: 0010（migrations 0001-0010）
- ADR 总数: 19（0001-0019）
- Benchmark 总数: 6（society_c / society_d / society_work / condense / persona_drift / multimodal）
- CLI 总数: 26 个 `we-together <sub>`

## 下一阶段候选（Phase 22+）

- Phase 22 规模与真依赖：100 万 person 压测 / imagehash / chromaprint / PG 后端
- Phase 23 真 HITL：branch_console 升级为完整 fastapi+htmx + rbac 整合
- Phase 24 多语言 prompt：prompts/templates 加 zh-CN / en / ja 三语版本
- Phase 25 联邦协议规范：`docs/superpowers/specs/federation-protocol.md` 正式 RFC
