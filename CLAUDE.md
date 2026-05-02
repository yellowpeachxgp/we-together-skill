# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

`we-together-skill` 是一个 **Skill-first 的社会图谱系统**：不是单人物蒸馏器，而是把人物、关系、群体、场景、事件、记忆、状态统一在一个 SQLite 图谱内核中，在 Skill 对话时按场景激活、演化。

## 常用命令

所有命令在仓库根目录执行：

```bash
# 运行全量测试（当前 122 passed）
.venv/bin/python -m pytest -q

# 运行单个测试
.venv/bin/python -m pytest tests/services/test_patch_application.py::test_apply_patch_record_can_create_memory -v

# 初始化数据库（必须先跑一次，bootstrap 会自动补齐 migrations/seeds 到 --root）
.venv/bin/python scripts/bootstrap.py --root .

# 端到端链路示例见 README.md «本地开发启动»；关键脚本：
#   create_scene / import_narration / import_text_chat / import_email_file
#   build_retrieval_package / record_dialogue / dialogue_turn
#   snapshot {list|rollback|replay} / merge_duplicates / graph_summary
```

## 架构总览

系统围绕 **事件先行、局部分支、留痕可回滚** 的原则组织。理解以下五条数据流即可定位大部分变更：

### 1. 导入链（`src/we_together/services/`）
- `ingestion_service.py` / `email_ingestion_service.py` / `file_ingestion_service.py` / `directory_ingestion_service.py` / `auto_ingestion_service.py`
- 每个 importer 的契约：读原始材料 → 创建 `event` + `raw_evidence` + `identity_links` → 调用 `patch_service.infer_*_patches()` 推理 patch → 通过 `patch_applier` 落图谱 → 写 `snapshot_entities`
- 共用 SQL 抽在 `ingestion_helpers.py`（`persist_import_job` / `persist_raw_evidence` / `persist_patch_record` / `persist_snapshot_with_entities`），新增 importer 时复用

### 2. Patch 系统（变更的唯一入口）
- `patch_service.build_patch()` 构造 patch 结构 dict
- `patch_service.infer_narration_patches / infer_text_chat_patches / infer_email_patches / infer_dialogue_patches` 推理 patch
- `patch_applier.apply_patch_record()` 单一入口，按 `operation` 分支：
  - `create_memory` / `update_state` / `link_entities` / `unlink_entities`
  - `create_local_branch` / `resolve_local_branch`（candidate 的 `effect_patches` 会被递归应用）
  - `update_entity` / `mark_inactive` / `merge_entities`
- unsupported operation 会把 patch 状态记为 `failed` 并抛 `ValueError`
- 每次成功 apply 都会 `invalidate_runtime_retrieval_cache()` 清理缓存
- **重要**：图谱所有结构性变更必须走 patch，不要直接 `INSERT/UPDATE` 业务表

### 3. Runtime Retrieval（`src/we_together/runtime/sqlite_retrieval.py`）
- `build_runtime_retrieval_package_from_db()` 是 Skill 运行时的唯一入口
- **有界激活传播**：从 scene_participants 起步 → 按 source_weights 拓展 `relation / event / group / memory` 派生 latent → 受 `activation_barrier` 预算限制 → 输出 `activation_budget` / `propagation_depth` / `source_counts`
- 检索包字段：`scene_summary` / `group_context` / `environment_constraints` / `participants` / `active_relations` / `relevant_memories` / `current_states` / `activation_map` / `response_policy` / `safety_and_budget` / `recent_changes`
- 预算裁剪参数：`max_memories` (默认 20) / `max_relations` (10) / `max_states` (30) / `max_recent_changes` (5)
- 缓存走 `retrieval_cache` 表，键为 `(scene_id, cache_type='runtime_retrieval', input_hash)`；默认 TTL = `DEFAULT_CACHE_TTL_SECONDS` = 3600
- **非 active 场景**（closed/archived）调用会抛 `ValueError`

### 4. 演化闭环（`dialogue_service.py`）
- `record_dialogue_event()` 记录对话事件 + 自动生成 snapshot
- `process_dialogue_turn()` 一键端到端：retrieval → record → infer → apply
- 对话演化产出的 patch 默认写 scene mood state + 多人共享 memory

### 5. Snapshot / 回滚（`snapshot_service.py`）
- `build_snapshot()` / `build_snapshot_entities()` 构造（不直接写库，由 importer/dialogue 自行持久化）
- `rollback_to_snapshot()` 删除式回滚：标记后续 patch 为 `rolled_back` → 删 states → 删后续 snapshots → 清 retrieval cache
- `replay_patches_after_snapshot()` 把 `rolled_back` 的 patch 重置为 pending 并逐个 apply，用于"重算"

## 存储层（`db/migrations/*.sql`）

6 个 migration 定义了完整 schema：

- **核心实体**：`persons` / `identity_links` / `relations` / `groups` / `group_members` / `memories` / `memory_owners` / `scenes` / `scene_participants` / `scene_active_relations` / `person_facets` / `relation_facets`
- **事件与关联**：`events` / `event_participants` / `event_targets` / `raw_evidence` / `import_jobs`
- **留痕演化**：`patches` / `snapshots` / `snapshot_entities` / `local_branches` / `branch_candidates`
- **候选中间层（Phase 4）**：`identity_candidates` / `event_candidates` / `facet_candidates` / `relation_clues` / `group_clues`
- **实体级链路**：`entity_links` / `states` / `entity_tags` / `entity_aliases`
- **运行时缓存**：`retrieval_cache`

## LLM 与 SkillRuntime（Phase 4-5）

- `src/we_together/llm/`：`LLMClient` Protocol + providers (mock/anthropic/openai_compat)；核心路径**不直接 import SDK**
- `get_llm_client(provider=None)` 依 `WE_TOGETHER_LLM_PROVIDER` 切换
- `runtime/skill_runtime.py`：`SkillRequest`/`SkillResponse`（平台无关）
- `runtime/prompt_composer.py`：retrieval_package → {system, messages}
- `runtime/adapters/`：Claude / OpenAI 两套适配器语义等价
- 端到端：`chat_service.run_turn()` 或 REPL `scripts/chat.py`

## 候选中间层与融合（Phase 4）

- `candidate_store.write_*` 把 importer / LLM 输出落到 `*_candidates` / `*_clues` 表
- `fusion_service.fuse_identity_candidates / fuse_relation_clues / fuse_all` 把候选升级为主图对象
- `llm_extraction_service.extract_candidates_from_text` 用 LLM 抽取 candidate
- 低置信 identity 冲突 → `create_local_branch` patch，不直接改主图
- `branch_resolver_service.auto_resolve_branches` 负责之后的自动 resolve

## 演化服务（Phase 6）

- `relation_drift_service.drift_relations()`：按 event 窗口重算 strength（+/-0.03..0.05）
- `state_decay_service.decay_states()`：按 decay_policy 衰减 confidence
- `_build_relevant_memories`：综合分 = type × relevance × confidence × recency × overlap × scene_match
- `scene_transition_service.suggest_next_scenes()`：下一场景推荐
- `self_activation_service.self_activate()`：无输入时的内心独白（Phase 7）

## 测试基线

- 每次切片严格遵循 **红灯 → 绿灯 → 全量回归 → git commit**
- `tests/conftest.py` 的 `temp_project_with_migrations` fixture 会把 migrations + seeds 拷进 tmp dir，然后调用 `bootstrap_project()`
- 新测试默认以此 fixture 为基础，不要假设任何图谱初始数据
- 时间敏感测试用 `datetime('now')` 或显式 `datetime.now(UTC)`

## 规约与约束（来自 docs/superpowers/specs/）

- **事件优先**：演化总是先写 event，再推理 patch，再改图谱
- **局部分支**：仅对未决歧义开 `local_branch`，不做整图分叉
- **默认自动化，底层可逆**：identity 融合激进合并，但通过 `merge_entities` 可追溯 `metadata_json.merged_into`
- **摘要是派生视图**：`persona_summary` / `style_summary` 等是派生字段，不是主存储
- **Skill-first / 通用型**：运行时逻辑不能绑死某一宿主平台

关键设计文档（当行为边界不清时优先查阅）：
- `docs/superpowers/state/current-status.md` — 能力边界快照
- `docs/superpowers/specs/2026-04-05-sqlite-schema-design.md`
- `docs/superpowers/specs/2026-04-05-patch-and-snapshot-design.md`
- `docs/superpowers/specs/2026-04-05-runtime-activation-and-flow-design.md`
- `docs/superpowers/specs/2026-04-05-runtime-retrieval-package-design.md`
- `docs/superpowers/specs/2026-04-05-identity-fusion-strategy.md`
