---
adr: 0052
title: Phase 44-50 综合 + 不变式扩展至 25 条
status: Accepted
date: 2026-04-19
---

# ADR 0052: Phase 44-50 综合 + 不变式扩展至 25 条

## 状态
Accepted — 2026-04-19

## 背景
Phase 44-50 让 v0.15 → v0.16：从"真 Skill 宿主落地 + 联邦 Read-Only MVP"跨入**插件生态 + 图谱时间 + 自修复 + 规模化 + 联邦安全 + i18n**。本 ADR 聚合新模式与新不变式。

## 决策

### D1. Plugin 架构让"可扩展"从口号变实体（ADR 0046）
- 4 类扩展点：Importer / Service / Provider / Hook
- Python entry_points 发现；核心 we-together 不为特定 importer/provider 硬编（#23）
- 这是走向社区的必要基础设施

### D2. 图谱有自己的时钟（ADR 0047）
- migration 0017 graph_clock 单行表
- `services/graph_clock.now()` fallback datetime.now(UTC)
- 时间敏感服务按需 opt-in 读 graph_clock（#24）
- 让"加速模拟一年"真可能，同时不破坏现有测试

### D3. 自修复闭环（ADR 0047）
- integrity_audit 纯读巡检
- self_repair 三档 policy：report_only / propose / auto
- auto 只做 safe fix；破坏性修复永远不 auto（#18 × #22 双闸门）

### D4. 规模化 50-500 人（ADR 0049）
- seed_society_m / seed_society_l CLI 可合成
- 性能基线：50 人 retrieval p95 < 1500ms
- sqlite-vec / faiss backend 就绪等真 extension 到位

### D5. 联邦从 MVP 升 v1.1（ADR 0050）
- Bearer token 鉴权 + rate limit 60/min + PII 自动脱敏
- 不变式 #25 强制所有跨图谱出口必须支持 PII mask + visibility 过滤

### D6. i18n + 时序可观测（ADR 0051）
- zh/en/ja 三语 prompt；detect_lang 启发式；plugin 可 register 新 key
- SVG sparkline 纯字符串零依赖
- webhook alerting 带 dry_run

### D7. Multi-Agent REPL（ADR 0048）
- orchestrate_dialogue 加互听、打断、私聊
- transcript → dialogue_event 入图谱

### D8. 不变式累计 → 25 条
ADR 0045 已有 22 条。v0.16 新增：

**#23**：扩展点必须通过 plugin registry 注册；核心代码不得为特定 importer/provider/service 硬编。

**#24**：时间敏感服务必须读 `graph_clock.now()` 优先，`datetime.now()` 仅限核心内核与无 db 上下文场景。

**#25**：任何跨进程 / 跨图谱出口（联邦 / 导出）必须支持 PII 脱敏与 visibility 过滤。

### D9. 三支柱 v0.16 达成度
- **A 严格工程化**：9.5 → **9.7**（3 条新不变式 + plugin API + graph_clock + i18n 文档）
- **B 通用型 Skill**：9.5 → **9.7**（plugin 让第三方扩展，联邦 v1.1 可真部署）
- **C 数字赛博生态圈**：8.5 → **9.0**（图谱时间 + 自修复 + 多 agent 互听 + 规模化）

## 版本锚点
- tag: `v0.16.0`
- 测试基线: **594 passed**（+73 over v0.15 的 521）
- ADR 总数: **52**（0001-0052）
- migration 数: **17**（+0017_graph_clock）
- benchmark 数: 10（未增）
- 不变式: **25**
- 新 service 模块: plugins / graph_clock / integrity_audit / self_repair / multi_agent_dialogue / federation_security / prompt_i18n / time_series_svg / webhook_alert
- 新 CLI: plugins_list / fix_graph / simulate_year / multi_agent_chat / seed_society_m / seed_society_l

## 下一阶段候选（Phase 51+，v0.17）

- **真 LLM 跑 tick 一年** + 成本归档 bench
- **真 sqlite-vec / faiss extension** 集成（目前 stub 阶段）
- **Claude Skills marketplace 上架**
- **PyPI 正式发布**
- **联邦写路径** + mTLS + audit log 持久化
- **tick 自动触发 archive_stale**
- **contradiction → unmerge → patch** 人工 gate workflow
- **mkdocs 真建站** + GitHub Pages
- **性能回归 CI baseline 自动对比**
- **plugin 签名**
- **4+ 语言支持**
- **REPL 交互式多 agent**（human 加入第 N 个 agent）

## 对外释出
建议：
- PyPI 发 v0.16.0（可选，需 token）
- GitHub 建 Release + 附 .weskill.zip + release_notes_v0.16.0.md
