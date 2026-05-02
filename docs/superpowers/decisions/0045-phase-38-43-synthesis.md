---
adr: 0045
title: Phase 38-43 综合 + 不变式扩展至 22 条
status: Accepted
date: 2026-04-19
---

# ADR 0045: Phase 38-43 综合 + 不变式扩展至 22 条

## 状态
Accepted — 2026-04-19

## 背景
Phase 38-43 让 v0.14 → v0.15：从"能跑但没人消费 + vision 未兑现"跨入**消费就绪 + tick 真归档 + 神经网格落地 + 图谱瘦身 + 联邦 MVP**。本 ADR 抽取共同模式与新不变式。

## 决策

### D1. "真被消费"路径完整化（B 支柱到达 9.5）
- SkillRuntime v1 冻结（ADR 0034）
- MCP 全协议（ADR 0035）
- Dashboard HTML + /metrics + e2e smoke（ADR 0040）
- 三份宿主接入文档
- 联邦 HTTP endpoint（ADR 0044）

三路宿主（Claude Desktop / Claude Code / OpenAI Assistants）都有可复制的接入文档。

### D2. "可持续演化"成闭环（C 支柱到达 8.5）
- Tick 编排（ADR 0036）
- Tick 真跑 + 归档（ADR 0041，首份 baseline 2026-04-18 已入仓库）
- Neural Mesh activation traces + plasticity（ADR 0042，vision "神经单元网格" 兑现）
- Forgetting + unmerge 闭环（ADR 0043，抗衡无限膨胀）

### D3. "对称可逆"升级为结构性不变式
- ADR 0033 #18 "主动写入必须经预算 + 偏好门控"
- 现在 ADR 0043 加 #22："图谱写入必须有对称的撤销路径"
- 这两条一起让"默认可逆 + 默认自动化"双原则真的成立

### D4. 不变式累计 → 22 条

ADR 0039 已有 20 条，本阶段新增：

**#21**：任何激活传播机制必须可 introspect（能画出"谁激活了谁、权重多少"）。
> 违反则神经网格变黑盒，无法调参、无法信任。

**#22**：图谱写入必须有对称的"撤销"路径（merge ↔ unmerge / archive ↔ reactivate / create ↔ mark_inactive / record ↔ rollback）。
> 违反则"默认可逆"失效；数据一旦写错就永久失真。

### D5. 三支柱 v0.15 达成度
- **A 严格工程化**：9.5 → **9.5**（维持，主要在重大新能力之间稳住不变式治理）
- **B 通用型 Skill**：8 → **9.5**（三路宿主文档齐 + Dashboard/metrics + 联邦 MVP 跑通）
- **C 数字赛博生态圈**：7 → **8.5**（tick 真归档 + 神经网格 + 遗忘 + 联邦）

## 版本锚点
- tag: `v0.15.0`
- 测试基线: **521 passed**（+44 over v0.14.0 的 477）
- ADR 总数: 45（0001-0045）
- migration 数: 16（+0016_activation_traces）
- benchmark 数: 10（+1 首份 tick_run）
- 不变式: **22**
- 新 service: time_simulator ↔ tick_sanity 闭环加强 / activation_trace / forgetting / entity_unmerge / federation_client
- 新 CLI: dashboard.py / skill_host_smoke.py / rollback_tick.py / activation_path.py / federation_http_server.py

## 下一阶段候选（Phase 44+，v0.16）

- **真 LLM 跑 tick**（需 key；本阶段全 Mock）→ 产出真成本报告
- **真 sqlite-vec / FAISS** 集成 + 100k 压测
- **联邦写路径 + 鉴权**（mTLS / Bearer）
- **tick 里自动触发 archive_stale_memories**
- **contradiction → unmerge → patch** 带人工 gate 的 workflow
- **Claude Skills marketplace 真上架**
- **multi_agent_chat.py REPL** 真多人对话
- **i18n prompts**
- **plugin/extension 机制**（第三方挂新 schema/service 不 fork）
- **tick 观测 dashboard trend**（时序图）

## 对外释出

建议 PyPI 发 v0.15.0（可选）；本仓库 git tag v0.15.0 已打。
