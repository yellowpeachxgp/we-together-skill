---
adr: 0059
title: Phase 51-57 综合 + 不变式扩展至 28 条
status: Accepted
date: 2026-04-19
---

# ADR 0059: Phase 51-57 综合 + 不变式扩展至 28 条

## 状态
Accepted — 2026-04-19

## 背景
Phase 51-57 让 v0.16 → v0.17：从"社会图谱"升到"世界图谱"，从"被动 agent"升到"自主 + 梦 + 学习"，从"孤立代码"升到"社区就绪 + 发布流程固化"。这不是加功能，是**维度跃迁**。

## 决策

### D1. 世界建模升维（ADR 0053）
- migration 0018 objects + 0019 places + 0020 projects
- 跨类 entity_links：person→owns→object / event→at→place / project→involves→person
- `world_service.active_world_for_scene` 返回 scene 级"活跃世界"
- 不变式 #26：世界对象必须有时间范围

### D2. AI Agent 元能力（ADR 0054）
- migration 0021 agent_drives + autonomous_actions
- `autonomous_agent`：compute_drives → decide_action → record_autonomous_action
- `dream_cycle`：archive + insight + learning
- 不变式 #27：自主行为必须可解释

### D3. 质量与韧性（ADR 0055）
- 可选 OpenTelemetry（NoOp 安全）
- property-based（Hypothesis optional）+ fuzz
- nightly workflow（UTC 02:00 smoke）

### D4. 社区就绪（ADR 0056）
- CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / GOVERNANCE 四件套
- 对比文档 vs Mem0 / Letta / LangMem
- mkdocs 骨架
- Good First Issues 20 条

### D5. 差异化能力（ADR 0057）
- `working_memory`：短时、per-scene、不落 db
- `derivation_rebuild`：insight / narrative / activation 派生可重建验证
- 不变式 #28：派生必须可重建

### D6. 发布准备（ADR 0058）
- PyPI checklist / Claude Skills 提交材料
- `release_prep.py --version X.Y.Z` 一键自检

### D7. 不变式累计 → 28 条
ADR 0052 已有 25 条。v0.17 新增：

**#26**：世界对象（object / place / project / event）必须有明确时间范围；"不存在"与"已失效"必须可区分。

**#27**：Agent 自主行为必须可解释——每次 autonomous_actions 必须能追溯到 drive / memory / trace 至少一个。

**#28**：所有派生字段（persona_summary / narrative_arcs / activation_map / insight / working_memory）必须可从底层 events / memories 重建。

### D8. 三支柱 v0.17 达成度
- **A 严格工程化**：9.7 → **9.8**（+3 条不变式 + OTel + property + fuzz + nightly）
- **B 通用型 Skill**：9.7 → **9.8**（社区就绪 4 件套 + 3 份对比 + PyPI checklist + Claude Skills 提交材料）
- **C 数字赛博生态圈**：9.0 → **9.5**（世界建模升维 + Agent 自主 + 梦循环 + 派生可重建）

## 版本锚点
- tag: `v0.17.0`
- 测试基线: **638 passed**（+44 over v0.16 的 594）
- ADR 总数: **59**（0001-0059）
- migration 数: **21**（+0018/0019/0020/0021）
- benchmark 数: 10（未增）
- 不变式: **28**
- 新 service 模块: world_service / autonomous_agent / dream_cycle / otel_exporter / working_memory / derivation_rebuild
- 新 CLI: world_cli / dream_cycle / release_prep
- 新治理文件: CONTRIBUTING / CODE_OF_CONDUCT / SECURITY / GOVERNANCE

## 下一阶段候选（Phase 58+，v0.18）

- 真 LLM 跑 simulate_year + 成本报告
- 真 sqlite-vec / faiss 集成
- Claude Skills 真提交（外部流程）
- PyPI 正式发布（v0.18.x）
- 联邦写路径 + mTLS
- narrative_v2 深度升级
- mkdocs-material 真建站部署
- task decomposition（多 agent 协作完成 goal）
- LLM-based drive 检测（当前是关键词启发）
- 多 world / 多租户真实装

## 对外释出
v0.17.0 建议：
- GitHub Release 含 `.weskill.zip` + release_notes_v0.17.0.md
- PyPI 可选 dry-run
- Claude Skills 提交材料 ready，审批由 Core Maintainer 判断时机
