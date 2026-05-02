---
adr: 0039
title: Phase 33-37 综合 + 不变式扩展至 20 条
status: Accepted
date: 2026-04-19
---

# ADR 0039: Phase 33-37 综合 + 不变式扩展至 20 条

## 状态
Accepted — 2026-04-19

## 背景
Phase 33-37 让 v0.13 → v0.14：从"已有多能力但没被真消费过 + 没持续演化"跨入**真 Skill 宿主 + 持续演化 tick + 媒体落盘 + 规模化债务清理**。本 ADR 抽取共同模式与新不变式。

## 决策

### D1. "宿主无关"从声明升级为验证
ADR 0019 宣称的"通用型 Skill"，此前只有 LLMClient 双路径在守；v0.14 起：
- SkillRequest/Response schema 冻结 v1（ADR 0034）
- 三路宿主适配：Claude / OpenAI / MCP spec-compliant（ADR 0035）
- `scripts/verify_skill_package.py` 做 zip roundtrip 校验

### D2. "持续演化"从概念升级为可跑闭环
之前 state_decay / relation_drift / proactive_scan 各自为战；v0.14 起：
- `time_simulator.run_tick` / `simulate` 统一编排（ADR 0036）
- tick 结束自动 snapshot（不变式 #20）
- `tick_sanity.evaluate` 健康度评估

### D3. "多模态"从 teaser 升级为落盘
Phase 32 只有 MockMultimodalClient；v0.14 起：
- migration 0015 `media_assets` + `media_refs`（ADR 0037）
- `media_asset_service` / `ocr_service.ocr_to_memory` / `transcribe_to_event`
- hash dedup + visibility 过滤

### D4. "规模化"从假设升级为审计
v0.14 对 60+ services 做 inventory，对 15 条 migration 做 audit（ADR 0038）：
- 确认无 dead service；3 条 recall + 3 条 relation 职责不重叠
- VectorIndex backend 扩展到 `sqlite_vec / faiss` stub（延迟 import）
- `scripts/bench_scale.py` 提供 10k+ 压测能力

### D5. 不变式累计 → 20 条
ADR 0033 已有 18 条，v0.14 新增：

**#19**：SkillRuntime 请求/响应 schema 必须版本化；破坏性变更需 v2，而不是 in-place 改字段。
> 违反则宿主适配器随内部扩展频繁破坏，B 支柱崩塌。

**#20**：tick 写入必须能在无人工干预下被 snapshot 回滚至任一时间点（闭环可逆）。
> 违反则持续演化无法纠错；"赛博生态圈"变成不可控漂流。

### D6. 三支柱 v0.14 达成度
- **A 严格工程化**：9/10 → **9.5/10**（service-inventory + migration-audit 把审计制度化）
- **B 通用型 Skill**：6/10 → **8/10**（schema v1 冻结 + MCP 全协议 + OpenAI demo）
- **C 数字赛博生态圈**：5/10 → **7/10**（tick 闭环 + 媒体落盘，距"无人值守一周自演化"还差真执行数据）

## 版本锚点
- tag: `v0.14.0`
- 测试基线: **477 passed**（+41）
- ADR 总数: 39（0001-0039）
- migration 数: 15（+0015 media_assets）
- benchmark 数: 9（+multimodal_retrieval_groundtruth）
- 不变式: **20**
- 新 service: time_simulator / tick_sanity / media_asset_service / ocr_service（4 个）

## 下一阶段候选（Phase 38+）
- **真联邦互通**（v0.15）：替换 federation_service stub，两 skill 实例互引 person
- **真 sqlite-vec / FAISS**（v0.15）：当前只有 stub，真接入后重跑 bench_scale
- **tick 真调度**（v0.15）：crontab / NATS-trigger / k8s CronJob examples
- **Claude Skills marketplace 真上架**（v0.15）
- **multi_agent_chat.py REPL** + 真人机混合对话（v0.15）
- **contradiction → patch 自动联动**（v0.16）
- **i18n prompts**（v0.16）
