# We Together SQLite Schema 设计稿

## 1. 文档目标

本文档定义 `we together` 第一阶段的 SQLite 主存储结构。

目标不是穷尽未来所有字段，而是明确：

- 哪些对象必须进 SQLite
- 哪些对象只保留结构化真相，哪些内容保留在文件系统
- 表如何按“规范对象 / 留痕对象 / 连接对象 / 检索对象”分层
- 第一阶段必须有哪些索引与约束

## 2. 设计原则

### 2.1 SQLite 存结构化真相

SQLite 负责规范对象、事件流、patch、snapshot、局部分支和索引关系。

长文本、原始材料副本、工程文档保留在文件系统。

### 2.2 主对象稳定，细节可扩展

第一阶段优先保证表边界稳定，不追求一次把所有业务字段完全铺满。

扩展信息优先放入：

- `json` 字段
- `metadata` 字段
- `facet` 子表

而不是频繁重构主表。

### 2.3 事件优先

不允许只改主对象不留痕。
所有重要变更都必须可回溯到：

- `event`
- `patch`
- `snapshot`

### 2.4 可逆优先

激进自动融合是允许的，但 schema 必须天然支持：

- merge
- split
- local branch
- snapshot rollback

## 3. 存储分层

第一阶段建议把表分成四层：

### 3.1 规范主对象层

- `persons`
- `identity_links`
- `relations`
- `groups`
- `scenes`
- `events`
- `memories`
- `states`

### 3.2 连接与子对象层

- `person_facets`
- `relation_facets`
- `group_members`
- `scene_participants`
- `scene_active_relations`
- `memory_owners`
- `event_participants`
- `event_targets`

### 3.3 留痕与演化层

- `import_jobs`
- `raw_evidences`
- `patches`
- `snapshots`
- `snapshot_entities`
- `local_branches`
- `branch_candidates`

### 3.4 索引与检索层

- `entity_tags`
- `entity_aliases`
- `entity_links`
- `retrieval_cache`

## 4. 规范主对象层

### 4.1 `persons`

用途：存储人物主对象。

建议字段：

- `person_id` TEXT PRIMARY KEY
- `primary_name` TEXT NOT NULL
- `status` TEXT NOT NULL
- `summary` TEXT
- `persona_summary` TEXT
- `work_summary` TEXT
- `life_summary` TEXT
- `style_summary` TEXT
- `boundary_summary` TEXT
- `confidence` REAL
- `metadata_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

说明：

- `summary` 类字段是结构化派生摘要，可以存，但不能替代 facet 与 evidence
- 长篇说明仍应保留在文件系统或派生视图中

### 4.2 `identity_links`

用途：外部身份映射。

建议字段：

- `identity_id` TEXT PRIMARY KEY
- `person_id` TEXT
- `platform` TEXT NOT NULL
- `external_id` TEXT
- `display_name` TEXT
- `contact_json` TEXT
- `org_json` TEXT
- `match_method` TEXT
- `confidence` REAL NOT NULL
- `is_user_confirmed` INTEGER NOT NULL DEFAULT 0
- `is_active` INTEGER NOT NULL DEFAULT 1
- `conflict_flags_json` TEXT
- `metadata_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

约束建议：

- `(platform, external_id)` 建唯一索引，但允许 `external_id` 为空

### 4.3 `relations`

用途：关系主对象。

建议字段：

- `relation_id` TEXT PRIMARY KEY
- `core_type` TEXT NOT NULL
- `custom_label` TEXT
- `summary` TEXT
- `directionality` TEXT
- `strength` REAL
- `stability` REAL
- `visibility` TEXT
- `status` TEXT NOT NULL
- `time_start` TEXT
- `time_end` TEXT
- `confidence` REAL
- `metadata_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

说明：

- 关系参与者不直接塞 JSON，使用连接表

### 4.4 `groups`

用途：长期群体主对象。

建议字段：

- `group_id` TEXT PRIMARY KEY
- `group_type` TEXT NOT NULL
- `name` TEXT
- `summary` TEXT
- `norms_summary` TEXT
- `status` TEXT NOT NULL
- `confidence` REAL
- `metadata_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 4.5 `scenes`

用途：运行时场景对象。

建议字段：

- `scene_id` TEXT PRIMARY KEY
- `scene_type` TEXT NOT NULL
- `group_id` TEXT
- `trigger_event_id` TEXT
- `scene_summary` TEXT
- `location_scope` TEXT
- `channel_scope` TEXT
- `visibility_scope` TEXT
- `time_scope` TEXT
- `role_scope` TEXT
- `access_scope` TEXT
- `privacy_scope` TEXT
- `activation_barrier` TEXT
- `environment_json` TEXT
- `status` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

说明：

- 核心环境参数优先单列
- 扩展环境参数进入 `environment_json`

### 4.6 `events`

用途：事件主对象。

建议字段：

- `event_id` TEXT PRIMARY KEY
- `event_type` TEXT NOT NULL
- `source_type` TEXT NOT NULL
- `scene_id` TEXT
- `group_id` TEXT
- `timestamp` TEXT NOT NULL
- `summary` TEXT
- `visibility_level` TEXT NOT NULL
- `confidence` REAL
- `is_structured` INTEGER NOT NULL DEFAULT 0
- `raw_evidence_refs_json` TEXT
- `metadata_json` TEXT
- `created_at` TEXT NOT NULL

事件可见级别建议：

- `visible`
- `latent`
- `internal`

### 4.7 `memories`

用途：记忆主对象。

建议字段：

- `memory_id` TEXT PRIMARY KEY
- `memory_type` TEXT NOT NULL
- `summary` TEXT NOT NULL
- `emotional_tone` TEXT
- `relevance_score` REAL
- `confidence` REAL
- `is_shared` INTEGER NOT NULL DEFAULT 0
- `status` TEXT NOT NULL
- `metadata_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 4.8 `states`

用途：动态状态快照。

建议字段：

- `state_id` TEXT PRIMARY KEY
- `scope_type` TEXT NOT NULL
- `scope_id` TEXT NOT NULL
- `state_type` TEXT NOT NULL
- `value_json` TEXT NOT NULL
- `confidence` REAL
- `is_inferred` INTEGER NOT NULL DEFAULT 1
- `decay_policy` TEXT
- `source_event_refs_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

约束建议：

- `(scope_type, scope_id, state_type)` 建唯一索引，表示当前快照只有一条主记录

## 5. 连接与子对象层

### 5.1 `person_facets`

用途：人物多面特征扩展表。

建议字段：

- `facet_id` TEXT PRIMARY KEY
- `person_id` TEXT NOT NULL
- `facet_type` TEXT NOT NULL
- `facet_key` TEXT NOT NULL
- `facet_value_json` TEXT NOT NULL
- `confidence` REAL
- `source_event_refs_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 5.2 `relation_facets`

用途：关系特征扩展表。

建议字段：

- `facet_id` TEXT PRIMARY KEY
- `relation_id` TEXT NOT NULL
- `facet_key` TEXT NOT NULL
- `facet_value_json` TEXT NOT NULL
- `confidence` REAL
- `source_event_refs_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

### 5.3 `group_members`

用途：群体成员关系。

建议字段：

- `group_id` TEXT NOT NULL
- `person_id` TEXT NOT NULL
- `role_label` TEXT
- `joined_at` TEXT
- `left_at` TEXT
- `status` TEXT NOT NULL
- `metadata_json` TEXT

主键建议：

- `(group_id, person_id, status)`

### 5.4 `scene_participants`

用途：场景参与者与运行时激活状态。

建议字段：

- `scene_id` TEXT NOT NULL
- `person_id` TEXT NOT NULL
- `activation_score` REAL
- `activation_state` TEXT NOT NULL
- `is_speaking` INTEGER NOT NULL DEFAULT 0
- `reason_json` TEXT
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

激活状态建议：

- `inactive`
- `latent`
- `explicit`

### 5.5 `scene_active_relations`

用途：记录某场景下被激活的关系。

建议字段：

- `scene_id` TEXT NOT NULL
- `relation_id` TEXT NOT NULL
- `activation_score` REAL
- `reason_json` TEXT
- `created_at` TEXT NOT NULL

### 5.6 `memory_owners`

用途：记忆归属与共享关系。

建议字段：

- `memory_id` TEXT NOT NULL
- `owner_type` TEXT NOT NULL
- `owner_id` TEXT NOT NULL
- `role_label` TEXT

### 5.7 `event_participants`

用途：事件参与者列表。

建议字段：

- `event_id` TEXT NOT NULL
- `person_id` TEXT NOT NULL
- `participant_role` TEXT

### 5.8 `event_targets`

用途：事件影响对象索引。

建议字段：

- `event_id` TEXT NOT NULL
- `target_type` TEXT NOT NULL
- `target_id` TEXT NOT NULL
- `impact_hint` TEXT

## 6. 留痕与演化层

### 6.1 `import_jobs`

用途：一次导入动作的边界对象。

建议字段：

- `import_job_id` TEXT PRIMARY KEY
- `source_type` TEXT NOT NULL
- `source_platform` TEXT
- `operator` TEXT
- `status` TEXT NOT NULL
- `stats_json` TEXT
- `error_log` TEXT
- `started_at` TEXT NOT NULL
- `finished_at` TEXT

### 6.2 `raw_evidences`

用途：原始证据索引表。

建议字段：

- `evidence_id` TEXT PRIMARY KEY
- `import_job_id` TEXT NOT NULL
- `source_type` TEXT NOT NULL
- `source_platform` TEXT
- `source_locator` TEXT
- `content_type` TEXT NOT NULL
- `normalized_text` TEXT
- `timestamp` TEXT
- `file_path` TEXT
- `content_hash` TEXT
- `metadata_json` TEXT
- `created_at` TEXT NOT NULL

说明：

- 原始全文可以只落文件系统
- SQLite 至少保留索引、hash、路径、时间、摘要文本

### 6.3 `patches`

用途：事件推理出的结构化变更。

建议字段：

- `patch_id` TEXT PRIMARY KEY
- `source_event_id` TEXT NOT NULL
- `target_type` TEXT NOT NULL
- `target_id` TEXT
- `operation` TEXT NOT NULL
- `payload_json` TEXT NOT NULL
- `confidence` REAL
- `reason` TEXT
- `status` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `applied_at` TEXT

### 6.4 `snapshots`

用途：阶段性图谱快照。

建议字段：

- `snapshot_id` TEXT PRIMARY KEY
- `based_on_snapshot_id` TEXT
- `trigger_event_id` TEXT
- `summary` TEXT
- `graph_hash` TEXT
- `created_at` TEXT NOT NULL

### 6.5 `snapshot_entities`

用途：记录某个快照包含哪些对象版本。

建议字段：

- `snapshot_id` TEXT NOT NULL
- `entity_type` TEXT NOT NULL
- `entity_id` TEXT NOT NULL
- `entity_hash` TEXT

### 6.6 `local_branches`

用途：局部分支主对象。

建议字段：

- `branch_id` TEXT PRIMARY KEY
- `scope_type` TEXT NOT NULL
- `scope_id` TEXT NOT NULL
- `status` TEXT NOT NULL
- `reason` TEXT
- `created_from_event_id` TEXT
- `created_at` TEXT NOT NULL
- `resolved_at` TEXT

### 6.7 `branch_candidates`

用途：局部分支下的候选解释。

建议字段：

- `candidate_id` TEXT PRIMARY KEY
- `branch_id` TEXT NOT NULL
- `label` TEXT
- `payload_json` TEXT NOT NULL
- `confidence` REAL
- `status` TEXT NOT NULL
- `created_at` TEXT NOT NULL

## 7. 索引与检索层

### 7.1 `entity_tags`

用途：统一标签索引。

建议字段：

- `entity_type` TEXT NOT NULL
- `entity_id` TEXT NOT NULL
- `tag` TEXT NOT NULL
- `weight` REAL

### 7.2 `entity_aliases`

用途：统一别名检索。

建议字段：

- `entity_type` TEXT NOT NULL
- `entity_id` TEXT NOT NULL
- `alias` TEXT NOT NULL
- `alias_type` TEXT

### 7.3 `entity_links`

用途：跨实体通用连接索引。

用于补充那些不值得单独建连接表，但又需要统一检索的弱连接。

建议字段：

- `from_type` TEXT NOT NULL
- `from_id` TEXT NOT NULL
- `relation_type` TEXT NOT NULL
- `to_type` TEXT NOT NULL
- `to_id` TEXT NOT NULL
- `weight` REAL
- `metadata_json` TEXT

### 7.4 `retrieval_cache`

用途：运行时检索包缓存。

建议字段：

- `cache_id` TEXT PRIMARY KEY
- `scene_id` TEXT
- `cache_type` TEXT NOT NULL
- `input_hash` TEXT NOT NULL
- `payload_json` TEXT NOT NULL
- `expires_at` TEXT
- `created_at` TEXT NOT NULL

说明：

第一阶段可选实现，但 schema 应预留。

## 8. 第一阶段必须有的索引

第一阶段建议至少建立以下索引：

- `identity_links(platform, external_id)`
- `identity_links(person_id)`
- `relations(core_type, status)`
- `group_members(group_id, status)`
- `scene_participants(scene_id, activation_state)`
- `events(timestamp)`
- `events(event_type, timestamp)`
- `memories(is_shared, status)`
- `states(scope_type, scope_id, state_type)`
- `raw_evidences(import_job_id)`
- `patches(source_event_id, status)`
- `local_branches(scope_type, scope_id, status)`
- `entity_aliases(alias)`
- `entity_tags(tag)`

## 9. 约束规则

### 9.1 主键规则

所有主对象使用稳定文本 ID，不使用自增整数作为系统主标识。

### 9.2 时间规则

所有时间字段统一使用 ISO 8601 字符串，避免多格式混乱。

### 9.3 JSON 规则

所有 `*_json` 字段必须存可解析 JSON，不允许伪 JSON 文本。

### 9.4 删除规则

第一阶段不建议物理删除主对象，优先：

- `status = inactive`
- `status = merged`
- `status = resolved`

### 9.5 事件与 patch 规则

重要结构变化必须满足：

- 有 `event`
- 有 `patch`
- patch 应用后才能改主对象

## 10. SQLite 与文件系统的边界

### 10.1 应留在文件系统的内容

- 原始聊天全文
- 原始文档副本
- 图片与 OCR 原文
- 导入日志
- 长篇摘要
- 工程文档

### 10.2 应保留在 SQLite 的引用

即使全文在文件系统，SQLite 也必须保存：

- 路径
- hash
- 来源
- 时间
- 与主对象的引用关系

### 10.3 硬规则

SQLite 是规范对象真相层。
文件系统是原始材料层与长文本派生视图层。
两者不能相互越权。

## 11. 第一阶段最小可实现版本

如果要压缩到最小实现，第一阶段至少应落地以下表：

- `persons`
- `identity_links`
- `relations`
- `groups`
- `scenes`
- `events`
- `memories`
- `states`
- `import_jobs`
- `raw_evidences`
- `patches`
- `snapshots`
- `local_branches`
- `scene_participants`
- `group_members`

其余表可以视节奏补齐。

## 12. 下一步建议

在本稿之后，建议继续撰写：

1. `Patch 与 Snapshot 设计稿`
2. `Identity 融合策略设计稿`
3. `运行时检索包格式设计稿`
4. `首版数据库迁移与初始化方案`

## 13. 结论

`we together` 第一阶段的 SQLite 不应被实现为一个只会存人物描述的简易表。

它应被实现为：

> **一个以规范主对象为核心、以事件与 patch 为主留痕、以局部分支与快照为可逆机制、并与文件系统严格分工的混合社会图谱数据库。**
"},{"path":"docs/superpowers/state/current-status.md","content":"# 当前状态\n\n日期：2026-04-05\n\n当前已完成：\n\n- 明确项目定位为 Skill-first 的社会图谱系统\n- 选定第一阶段锚点场景为 `C：混合小社会`\n- 确定采用统一社会图谱内核，而不是工作/亲密双系统拼接\n- 确定关系模型为“核心维度固定 + 自定义扩展 + 自然语言摘要”\n- 确定导入策略为默认全自动、自动入图谱\n- 确定身份融合策略为激进自动融合，但必须可逆、可追溯\n- 确定演化策略为“先写事件，再归并入图谱”\n- 确定留痕模型为 Git 式混合结构\n- 确定第一阶段只支持局部分支，不支持整图分叉\n- 确定运行时采用“有界激活传播模型”\n- 确定环境参数采用“核心维度固定 + 自定义扩展”\n- 确定主存储采用 SQLite 与文件系统的混合模型\n- 确定 importer 采用“统一证据层 + 候选层”的输出契约\n- 确定 SQLite 为规范主对象与留痕对象的核心存储层\n\n当前主设计稿：\n\n- [2026-04-05-we-together-core-design.md](../specs/2026-04-05-we-together-core-design.md)\n- [2026-04-05-runtime-activation-and-flow-design.md](../specs/2026-04-05-runtime-activation-and-flow-design.md)\n- [2026-04-05-unified-importer-contract.md](../specs/2026-04-05-unified-importer-contract.md)\n- [2026-04-05-sqlite-schema-design.md](../specs/2026-04-05-sqlite-schema-design.md)\n\n下一步建议：\n\n- 定义 patch 与 snapshot 结构\n- 定义 identity 融合策略\n- 定义运行时检索包格式\n"}]}♀♀♀♀♀♀analysis to=functions.mcp__Github__push_files ￣第四色json
