# ADR 0002: LLM 在回路 + 统一候选中间层

## 状态

Accepted — 2026-04-17

## 背景

截至 Phase 3 末尾，we-together-skill 的 patch 推理全部基于关键词规则（如 `"累"` → energy=low）。这在工程骨架阶段验证了图谱内核可用性，但与 `vision/product-mandate.md` 中"自适应 / 可扩展 / 神经单元网格式演化"的要求存在明显差距：

1. 规则无法理解未知语境，导入真实聊天/邮件时召回率极低
2. `unified-importer-contract.md` 定义的 `IdentityCandidate / EventCandidate / FacetCandidate / RelationClue / GroupClue` 五类候选对象一直停留在文档层
3. 当 LLM 置信度分层（high/medium/low）时，系统需要一种"暂不决策"的机制，而当前版本会直接 auto-merge

## 决策

### D1. 引入 LLMClient 抽象（Slice M）

`src/we_together/llm/` 下建立最小抽象：

- `LLMClient` Protocol：只暴露 `chat()` / `chat_json()`
- `providers/mock.py`：所有测试默认走的 MockLLMClient（scripted responses）
- `providers/anthropic.py` / `providers/openai_compat.py`：延迟 import 真实 SDK
- `factory.get_llm_client(provider=None)`：按环境变量 `WE_TOGETHER_LLM_PROVIDER` 切换

**关键约束**：
- 核心代码路径**不得**直接 `import anthropic` 或 `import openai`，只能通过 factory 获得 client
- 单元测试**必须**使用 MockLLMClient，不得依赖网络/API Key
- 真实 provider 的参数通过 `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `OPENAI_BASE_URL` 环境变量注入

### D2. 候选中间层落地（Slice L）

新增 migration 0006 定义 5 张候选表：`identity_candidates` / `event_candidates` / `facet_candidates` / `relation_clues` / `group_clues`。

每张表共享 schema 模式：
- `candidate_id / clue_id` 主键
- `evidence_id` FK → `raw_evidences`
- `confidence REAL NOT NULL` + `confidence_tier` (high/medium/low)
- `status TEXT` (open/linked/rejected)
- `linked_*_id` 指向落地后的主对象

导入链路调整为两步：

```
importer → raw_evidences + candidate_store.write_*  (只写候选)
         → fusion_service.fuse_*  (将候选升级为主对象 + patch)
```

### D3. Fusion 策略（Slice N）

`fusion_service.fuse_identity_candidates()`：
- `(platform, external_id)` 匹配 → 复用已有 person
- 同名匹配 → 高/中置信直接 reuse；低置信触发 D4
- 均不命中 → 新建 person

`fusion_service.fuse_relation_clues()`：
- 参与者必须都已 `linked` 到 person，否则跳过
- 相同 `core_type` 视为同一关系
- 通过 `event_targets` 把 relation 挂到 retrieval 路径

### D4. 置信度分层 + 自动分支（Slice O）

当 `confidence_tier == 'low'` 且发生身份冲突（同名但 external_id 不同）时，系统**不直接合并**，而是通过 `create_local_branch` patch 开一个 "person" scope 的 branch，含两个 candidates：
- `cand_merge`：合并到现有 person
- `cand_new`：新建独立 person

这对齐了 `core-design.md` §9.3 "分支只用于未决歧义" 的约定：低置信度永远等人工决策（或更高证据出现），不直接改变图谱真相。

### D5. 降级策略

没有 LLM 配置时系统必须仍然可用：
- 导入路径退回到现有的关键词规则 patch 推理（`infer_narration_patches` 等）
- `chat_service.run_turn` 以 mock provider 默认返回占位文本，图谱演化逻辑仍然跑完整链

## 后果

### 正面
- `importer` 可以真正吃真实聊天/邮件/文档，不依赖硬编码关键词
- 新平台 importer 只需要输出 candidate，无需理解图谱内部
- 真实 LLM（Claude/OpenAI）都通过同一 Protocol 接入，符合"通用型 Skill"约束
- 测试套件无需网络，单元测试 mock 即可

### 负面 / 权衡
- 多了一层 candidate → fusion 的转换，导入性能略下降（但可接受，批量跑）
- LLM 抽取结果不稳定时，低置信分支会堆积；需要配合 Phase 6 的"人工裁决 UI"或自动化裁决机制

### 后续
- Phase 5 会在此基础上增加 `prompt_composer` / `SkillRuntime` / adapters（已完成）
- Phase 6 需要增加 branch 自动关闭策略（当新证据把置信度推高时）
- Phase 7 考虑引入"候选去重器"：同一 evidence 多次导入时不重复生成 candidate
