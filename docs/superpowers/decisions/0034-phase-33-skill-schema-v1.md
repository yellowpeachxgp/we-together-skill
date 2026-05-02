---
adr: 0034
title: Phase 33 — SkillRuntime v1 Schema 冻结
status: Accepted
date: 2026-04-19
---

# ADR 0034: Phase 33 — SkillRuntime v1 Schema 冻结

## 状态
Accepted — 2026-04-19

## 背景
ADR 0019 引入 SkillRuntime，之后 Phase 23 加 `tools`、Phase 25 加 streaming、Phase 28 加 `query_text` rerank。字段累计扩充但**从未冻结版本**，宿主适配器每次都要跟着改；这与 B 支柱"通用型 Skill"的长期稳定目标相悖。

## 决策

### D1. SkillRequest / SkillResponse 加 `schema_version` 字段
- 值为 "1"（常量 `SKILL_SCHEMA_VERSION`）
- `to_dict()` 写入；`from_dict()` 校验；不匹配抛 `ValueError`
- 默认值让现有创建路径不变（向后兼容 runtime 代码；序列化变更）

### D2. v1 字段集冻结
v1 包含且仅包含：
- `schema_version: str`
- `system_prompt: str`
- `messages: list[{role, content}]`
- `retrieval_package: dict`
- `scene_id: str`
- `user_input: str`
- `metadata: dict`
- `tools: list[{name, description, input_schema}]`

Response v1：`text / speaker_person_id / supporting_speakers / usage / raw / schema_version`

### D3. 后续扩展规则
- **Additive-only**：v1 内只能新加可选字段（带 default），不能删/改现有字段
- 破坏性变更一律开 `v2`，by 新 `SkillRequestV2` 类，不是 in-place 改 v1
- 各 adapter（Claude / OpenAI / MCP / Feishu / LangChain / Coze）收 v1 请求时做 payload build，不依赖具体字段存在性以外的假设

## 不变式（v0.14.0 确立为第 19 条，见 ADR 0039）
**#19**：SkillRuntime 请求/响应 schema 必须版本化；破坏性变更需 v2，而不是 in-place 改字段。

## 版本锚点
- tests: +3（roundtrip / reject wrong version / adapter payload 等价）
- 文件: `runtime/skill_runtime.py` 加 `SKILL_SCHEMA_VERSION` + `from_dict`

## 拒绝的备选
- 直接发 `SkillRequest v2` 替换 v1：过早，v1 字段尚未真正被外部消费过；先冻结 v1 才有 v2 的基准
- 不版本化只靠 git：git 无法让**运行时**区分请求源的 schema 年代
