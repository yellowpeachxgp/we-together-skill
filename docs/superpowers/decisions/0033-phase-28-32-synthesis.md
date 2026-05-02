---
adr: 0033
title: Phase 28-32 综合 + 不变式扩展至 18 条
status: Accepted
date: 2026-04-19
---

# ADR 0033: Phase 28-32 综合 + 不变式扩展至 18 条

## 状态
Accepted — 2026-04-19

## 背景
Phase 28-32 让 v0.12 → v0.13：从"向量化 demo + 单 agent runtime"跨入**规模可用的多智能体 + 主动 + 自检 + 跨模态骨架**。本 ADR 抽取共同模式与新不变式。

## 决策

### D1. 三层"自主性"分级
所有"图谱主动行为"分三级，每级有显式开关与可观测：
| 层 | 触发 | 例子 | 默认 |
|----|------|------|------|
| L0 被动 | 用户输入 | importer / dialogue | always-on |
| L1 周期 | scheduled | proactive_scan / state_decay | opt-in |
| L2 自检 | runtime trigger | contradiction_detector | report-only |

L1 必须经预算 + 偏好门控；L2 默认只读，不写图。

### D2. "Backend 抽象 + 默认 SQLite + 真后端延迟 import"
扩展自 ADR 0027 D1（双路径），现在涵盖 storage / vector / queue / multimodal：
- storage: SQLiteBackend / PGBackend
- vector: flat_python / 未来 sqlite-vec / faiss
- queue: mock / NATS
- multimodal: MockMultimodalClient / CLIPStubClient

均：默认 mock，真 backend 延迟 import，import 失败 raise 友好提示。

### D3. 不变式累计 → 18 条
ADR 0027 已有 16 条，本阶段新增：

**17. 多 agent 必须共享底层图谱真理，不允许在 agent 内部派生独立 memory store**。private vs shared 是查询过滤，不是物理拷贝。
> 违反则丢失"图谱即真理"原则，多 agent 之间出现分裂。

**18. 主动写入（L1/L2）必须经显式预算 + 用户偏好（mute/consent）门控**。Detection-only 服务不允许直接改业务表。
> 违反则用户被打扰；图谱出现"自动错改"。

### D4. 文档与 Skill 接口稳定性
- ADR / mega-plan / current-status 三件套继续保持
- Skill 入口 `we_together.runtime.SkillRuntime` 接口本阶段无破坏性变更
- 新增功能均通过 optional extras 提供，core install 体积零增长

## 版本锚点
- tag: `v0.13.0`
- 测试基线: **436 passed**
- ADR 总数: 33（0001-0033）
- migration 数: 14（新增 0014_proactive_prefs）
- benchmark 数: 8（新增 contradiction_groundtruth）
- coverage: ~90%

## 下一阶段候选（Phase 33+）
- sqlite-vec / FAISS 真集成 + 1M 规模压测报告
- 多 agent REPL（multi_agent_chat.py）+ Phase 30 simulate_week.py
- 真 cron / NATS-trigger 调度 proactive_scan
- contradiction → patch 自动联动（高置信 → create_local_branch）
- multimodal 真接入：media_assets migration + Skill 渲染图片消息
- federation interop 真 RPC（替换 v0.10 stub）
