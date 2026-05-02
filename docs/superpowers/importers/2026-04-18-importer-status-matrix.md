# Importer 状态矩阵（已实现层）

> **定位**：本文档描述当前仓库里 **已实现** 的 importer 服务的契约、输入输出、推理行为和限制。与 `2026-04-05-importer-reuse-matrix.md`（描述外部项目复用计划）互补。
>
> **版本**：2026-04-18。随 importer 变更同步。

## 0. 总览矩阵

| importer | 入口函数 | 输入形态 | LLM 参与 | 生成 patch 类型 | 是否会开 local_branch | 落库实体 |
|---|---|---|---|---|---|---|
| narration | `ingest_narration(db_path, text, source_name)` | 自由文本（旁白叙述） | 否 | `create_memory`、`update_state`、`update_entity` | 否（置信度保守） | events, memories, states, persons, relations |
| text_chat | `ingest_text_chat(db_path, transcript, source_name)` | `小X: ... / 小Y: ...` 格式对话 | 否 | `create_memory`、`link_entities` | 否 | events, memories, persons, relations |
| email | `ingest_email_file(db_path, email_path)` | `.eml` 文件 | 否 | `create_memory`、`link_entities` | 否 | events, memories, persons |
| wechat_text | `import_wechat_text(db_path, csv_path, chat_name=None)` | CSV（time/sender/content） | 否 | 仅写 raw_evidence + identity_candidates；**不直接落主图** | 由后续 fuse_all 决定 | raw_evidence, identity_candidates, event_candidates, group_clues |
| auto_text | `auto_ingest_text(db_path, text, source_name)` | 自由文本 | 否 | 同 narration/text_chat（按 `detect_import_mode` 分派） | 否 | 同上游 |
| file_auto | `ingest_file_auto(db_path, file_path)` | `.txt / .md / .eml` | 否 | 同上游 | 否 | 同上游 |
| directory | `ingest_directory(db_path, directory)` | 目录（批量 .txt/.md/.eml） | 否 | 逐文件分派 | 否 | 同上游 |
| llm_extraction | `extract_candidates_from_text(db_path, text, source_name, provider=None)` | 自由文本 | **是** | 写候选中间层；不直接落主图 | 由后续 fuse_all 决定 | raw_evidence, identity_candidates, event_candidates, relation_clues, group_clues |

## 1. 共用契约（所有 importer）

**输入侧不变量**：

- `db_path` 指向 `bootstrap_project(...)` 初始化过的 SQLite 数据库。
- `source_name` / 文件名用于 `import_jobs.source_name` 与 `raw_evidence.source_name`。

**落库侧不变量**（由 `ingestion_helpers` 集中实现）：

- 每次成功导入生成 **一条 `import_jobs` 记录** + **至少一条 `raw_evidence`**。
- 结构性变更**仅通过 patch**（`persist_patch_record` → `apply_patch_record`）。
- 每次导入后写 **一份 `snapshots` + `snapshot_entities` 集合**，用于回滚与 diff。
- `patch_applier` 成功后自动 `invalidate_runtime_retrieval_cache()`。

**不变式**：

- 不直接 `INSERT/UPDATE` 业务表（persons/relations/memories/states）。
- identity 关联通过 `identity_link_service.upsert_identity_link` 建立 `identity_links` 行。

## 2. importer 详情

### 2.1 narration

- **用途**：用户口述/粘贴的叙述文本。
- **推理函数**：`patch_service.infer_narration_patches`。
- **行为**：
  - 用极简正则提取 `小X 和 小Y` 形式的 person 对。
  - 为每个 person 生成 `update_entity` patch（首次创建 person）。
  - 为文本中的 sentiment 片段生成 `create_memory`（`memory_type = shared_memory`）。
  - 没有 LLM 参与；不会开 local_branch。
- **置信度**：patch confidence ~0.6。
- **已知限制**：正则只识别 `小+中文` 格式人名；别名/英文名不会被识别（走 `llm_extraction` 或 `wechat_text`）。

### 2.2 text_chat

- **用途**：结构化对话文本 `角色: 内容` 多行。
- **推理函数**：`patch_service.infer_text_chat_patches`。
- **行为**：
  - 按 `角色:` 拆轮次 → 生成 dialogue_event。
  - 角色名未映射到 person 时，走 `upsert_identity_link` 创建 person + identity_link。
  - 为整段对话产出 1~N 条 `create_memory`（内容摘要 + 参与者）。
  - 两人以上时为 pair 产出 `link_entities` (from=person, to=person, relation_type='dialogue_partner')。
- **置信度**：~0.65。

### 2.3 email

- **用途**：单封 `.eml` 文件导入。
- **推理函数**：`patch_service.infer_email_patches`。
- **行为**：
  - 解析 header (`From`, `To`, `Subject`, `Date`) → 生成 event。
  - 发件人/收件人各生成 identity_link；未存在的 person 由 `upsert_identity_link` 创建。
  - Body 作为 memory summary。
- **置信度**：~0.7（header 来源强于正文）。

### 2.4 wechat_text（Slice X1）

- **用途**：微信聊天记录 CSV 原型 importer。
- **特殊性**：
  - **仅写候选中间层**：`identity_candidates / event_candidates / group_clues`。
  - **不直接改主图**；下游由 `fusion_service.fuse_all(db_path)` 决定是否升级为 person / relation / group。
  - 群聊判定：`_looks_like_group(chat_name)` — 若聊天名含"群"或 ≥3 个独立 sender 则归为 group。
- **落库**：`raw_evidence.source_name='wechat_text'` + `import_jobs.source_type='wechat_text'`。

### 2.5 auto_text / file_auto / directory

- **用途**：调度层，不自己推理。
- **分派规则**：
  - `auto_text`：`detect_import_mode(text)` → text_chat 还是 narration。
  - `file_auto`：`detect_file_mode(path)` → email 或 text。
  - `directory`：遍历目录，逐文件调 `file_auto`；`SUPPORTED_SUFFIXES = {.txt, .md, .eml}`；其他扩展名进 `skipped`。
- **返回**：在上游返回 dict 上再加一层 `mode` / `content_mode` 指示实际走了哪条路径。

### 2.6 llm_extraction（Slice N2）

- **用途**：用 LLM 从自由文本抽取结构化候选。
- **依赖**：`we_together.llm.LLMClient`（provider 由 `WE_TOGETHER_LLM_PROVIDER` 切换，默认 mock）。
- **行为**：
  - 一次 LLM 调用产出 `{ identity_candidates, relation_clues, group_clues, event_candidates }`。
  - 落 `raw_evidence` 后写到对应候选表；**不直接改主图**。
- **升级路径**：`fusion_service.fuse_all()` 把候选升级为 person / relation / group，低置信 identity 冲突会触发 `create_local_branch` patch。

## 3. 融合与分支行为（候选型 importer 的下游）

`wechat_text` 与 `llm_extraction` 属于 **候选型 importer**。它们的输出不会立即显示在 runtime_retrieval 里，必须经过 `fusion_service`：

- `fuse_identity_candidates`：
  - 同名且 display_name 完全一致 → 升级为 person（或合并到已有 person）。
  - 同名但 identity_links 矛盾（如 alias 冲突、confidence 低）→ 开 `local_branch`（`patch_applier.create_local_branch`），由 `branch_resolver_service.auto_resolve_branches` 后续处理。
- `fuse_relation_clues`：基于 clues 的共现次数与 sentiment，产出 `update_entity`（relations.strength）。
- `fuse_group_clues`：同 chat_name 聚合 → 创建 group + group_members。

## 4. 与 runtime_retrieval 的可见性

| importer | retrieval 可见延迟 |
|---|---|
| narration / text_chat / email / auto_text / file_auto / directory | 同步，导入后缓存失效，下一次 `build_runtime_retrieval_package_from_db` 即可见。 |
| wechat_text / llm_extraction | **需先跑 `fuse_all`**；未融合前，retrieval 不感知候选表。 |

## 5. 测试覆盖

每个 importer 都有对应测试：

- `tests/services/test_narration_ingestion.py`
- `tests/services/test_text_chat_ingestion.py`
- `tests/services/test_email_ingestion.py`
- `tests/services/test_auto_ingestion.py`
- `tests/services/test_file_ingestion.py`
- `tests/services/test_directory_ingestion.py`
- `tests/services/test_wechat_text_importer.py`
- `tests/services/test_llm_extraction.py`
- `tests/services/test_fusion_service.py`

## 6. 维护提示

新增 importer 时必须：

1. 复用 `ingestion_helpers`（persist_import_job / persist_raw_evidence / persist_patch_record / persist_snapshot_with_entities）。
2. 定义推理函数在 `patch_service.py`（如 `infer_<X>_patches`），不要在 importer 里直写 patch dict。
3. 对同一自然人的多来源数据，通过 `upsert_identity_link` 归一。
4. 低置信冲突走 `create_local_branch` 而非直接修改主图。
5. 更新本文档第 0 节的总览矩阵。
