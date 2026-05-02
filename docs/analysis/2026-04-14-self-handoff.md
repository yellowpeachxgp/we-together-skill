# We Together Self Handoff

日期：2026-04-14

用途：给重启后的新会话中的 Codex / Claude 作为“自我接力”文档，帮助其在最短时间内恢复到当前工程节点。

范围：仅针对 `/Users/yellowpeachmac/mac-code/mac-code/we-together-skill`

---

## 1. 仓库与验证基线

- 项目目录：`/Users/yellowpeachmac/mac-code/mac-code/we-together-skill`
- 上层 Git 仓库：`/Users/yellowpeachmac/mac-code/mac-code`
- 当前 HEAD：`7302f98b7c75cddb4c6139b23c363832ce0e9eb6`
- 最新提交标题：`docs: Phase 3 文档同步`

最新提交链：

```text
7302f98 docs: Phase 3 文档同步
77c3521 feat: snapshot patch 重放
5b64bb9 feat: 近期变更上下文 recent_changes
421f0a8 feat: 检索包预算裁剪 max_memories / max_relations / max_states
49c9ed7 feat: 场景生命周期 close / archive
fa26273 feat: process_dialogue_turn 端到端闭环
684c2b4 feat: merge_entities patch + identity 自动合并
fe625f9 docs: Phase 2 文档同步
c205cea feat: update_entity 通用实体更新 patch
03bd6f2 feat: snapshot 历史遍历与回滚服务
c2b28e4 feat: 对话 patch 推理闭合演化循环
b29d0cb feat: 对话事件记录服务 + CLI
```

fresh 全量验证证据：

```bash
cd /Users/yellowpeachmac/mac-code/mac-code/we-together-skill
.venv/bin/python -m pytest -q
```

输出：

```text
122 passed in 3.11s
```

重要说明：

- `confirmed`：项目目录本身当前没有未提交代码变更需要处理。
- `confirmed`：上层仓库仍有与本项目无关的脏状态：
  - `.DS_Store`
  - `bilibili/`
- `confirmed`：接手时不要误处理这两个非项目内容。

---

## 2. 最高优先级约束

以下约束高于具体实现：

1. 严格工程化推进。
2. 所有能力都必须可追踪、可验证、可归档、可回滚。
3. 产品是 `skill-first` 的社会图谱内核，不是一次性脚本。
4. 核心演化链固定为：
   `Event -> Patch -> Graph State -> Snapshot`
5. 场景优先。
6. 当前响应永远由 `Scene` 驱动，不做无边界全图参与。
7. 默认自动化。
8. 能自动推理的，不交给用户手工维护。
9. 摘要只是派生视图，不能替代结构化主存储。
10. 不要把“设计稿里的未来能力”说成“已经实现”。
11. 每个稳定节点都必须同步：
    - `README.md`
    - `SKILL.md`
    - `docs/superpowers/state/current-status.md`
12. 每次宣称完成前都必须基于 fresh verification。
13. 只提交 `we-together-skill/`，不要碰上层仓库其他无关内容。

---

## 3. 项目意义

`we together.skill` 的目标不是“单人物蒸馏”，而是：

- 导入多人物、多来源材料、多层关系
- 构建统一社会图谱
- 在运行时按场景、关系、记忆、状态、预算、约束做有界激活
- 让每次导入或对话都沉淀为事件，再通过结构化 patch 进入图谱
- 最终形成一个可扩展、可解释、可追责的数字社会 skill 内核

一句话：

> 这是一个从“数字人格”迈向“数字社会图谱”的工程化产品内核。

---

## 4. Code Truth Baseline

### 4.1 架构真相

- `confirmed`：核心代码位于 `src/we_together/`，按 `db / domain / importers / runtime / services` 切分。
- `confirmed`：主要入口是 CLI 脚本，而不是宿主 SDK。
- `confirmed`：当前项目已经是可运行原型，不只是设计仓库。
- `confirmed`：主存储是 SQLite，长文本和工程文档在文件系统。
- `confirmed`：运行时主实现集中在 [`src/we_together/runtime/sqlite_retrieval.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/src/we_together/runtime/sqlite_retrieval.py)。

### 4.2 主要快乐路径

#### 路径 A：导入文本 narration

`confirmed`

1. `import_narration.py`
2. `ingestion_service.ingest_narration()`
3. 写入 `import_jobs / raw_evidences / events / persons / relations`
4. 通过 `infer_narration_patches()` 生成结构化 patch
5. 通过 `apply_patch_record()` 应用 `create_memory / link_entities / update_state`
6. 写入 `snapshots / snapshot_entities`

证据：

- [`src/we_together/services/ingestion_service.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/src/we_together/services/ingestion_service.py)
- [`tests/services/test_narration_ingestion_pipeline.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/tests/services/test_narration_ingestion_pipeline.py)

#### 路径 B：导入 text chat

`confirmed`

1. `import_text_chat.py`
2. `ingestion_service.ingest_text_chat()`
3. 写入 message events 和 `event_participants`
4. 建 relation，挂到 `event_targets`
5. 通过 `infer_text_chat_patches()` 落 memory / relation-link / state
6. 写入 `snapshots / snapshot_entities`

证据：

- [`src/we_together/services/patch_service.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/src/we_together/services/patch_service.py)
- [`src/we_together/services/ingestion_service.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/src/we_together/services/ingestion_service.py)
- [`tests/services/test_text_chat_ingestion_pipeline.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/tests/services/test_text_chat_ingestion_pipeline.py)

#### 路径 C：构建 retrieval package

`confirmed`

1. `build_retrieval_package.py`
2. `runtime/sqlite_retrieval.build_runtime_retrieval_package_from_db()`
3. 优先尝试 `retrieval_cache`
4. 构建 participants / active_relations / memories / states / activation_map / response_policy / safety_and_budget
5. 刷新 `scene_active_relations`
6. 必要时写回缓存

证据：

- [`src/we_together/runtime/sqlite_retrieval.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/src/we_together/runtime/sqlite_retrieval.py)
- [`tests/runtime/test_db_retrieval_package.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/tests/runtime/test_db_retrieval_package.py)
- [`tests/test_cli_workflow.py`](/Users/yellowpeachmac/mac-code/mac-code/we-together-skill/tests/test_cli_workflow.py)

---

## 5. 报告核对结论

用户给的 Claude 报告中，以下点已通过代码或测试核对：

### 5.1 已核对为 confirmed

- `confirmed`：`merge_entities` patch 已存在。
  - 证据：`patch_applier.py` 中有 `merge_entities` 分支。
  - 证据：`tests/services/test_patch_application.py` 中有对应测试。

- `confirmed`：`find_and_merge_duplicates()` 已存在。
  - 证据：`identity_fusion_service.py`
  - 证据：`tests/services/test_identity_fusion.py`

- `confirmed`：`process_dialogue_turn()` 已存在并有端到端测试。
  - 证据：`dialogue_service.py`
  - 证据：`tests/services/test_dialogue_service.py`

- `confirmed`：`close_scene()` / `archive_scene()` 已存在。
  - 证据：`scene_service.py`
  - 证据：`tests/services/test_scene_service.py`

- `confirmed`：retrieval budget 裁剪参数已存在：
  - `max_memories`
  - `max_relations`
  - `max_states`
  - `max_recent_changes`
  - 证据：`sqlite_retrieval.py`
  - 证据：`tests/runtime/test_db_retrieval_package.py`

- `confirmed`：`recent_changes` 已存在。
  - 证据：`sqlite_retrieval.py` 中 `_build_recent_changes()`
  - 证据：对应 runtime 测试

- `confirmed`：`replay_patches_after_snapshot()` 已存在。
  - 证据：`snapshot_service.py`
  - 证据：`tests/services/test_snapshot_service.py`

### 5.2 已核对为 confirmed，但需注意边界

- `confirmed`：文档声称当前全量测试通过 `122 passed`，已被 fresh 验证确认。
- `confirmed`：`graph_summary` 已经比早期版本更强，但仍然是工程观测入口，不是完整运维面板。
- `confirmed`：`retrieval_cache` 已经可写、可读、可失效，但仍是最小版，没有复杂 TTL / 元数据矩阵。

### 5.3 轻微 drift

- `confirmed`：`docs/superpowers/state/current-status.md` 的日期是 `2026-04-12`，而当前系统日期是 `2026-04-14`。
- `inferred`：这更像文档日期没继续更新，而不是代码状态错误。

---

## 6. 当前实现能力清单

### 6.1 导入层

`confirmed`

- narration
- text_chat
- email
- auto text route
- file auto route
- directory route

### 6.2 patch / evolution

`confirmed`

支持的 patch 操作至少包括：

- `create_memory`
- `update_state`
- `link_entities`
- `unlink_entities`
- `create_local_branch`
- `resolve_local_branch`
- `mark_inactive`
- `merge_entities`
- `update_entity`

### 6.3 运行时

`confirmed`

已具备：

- bounded activation 初级版本
- source weights
- source counts
- event decay
- budget limits
- recent changes
- branch risk 暴露
- retrieval cache
- scene_active_relations 刷新

### 6.4 traceability

`confirmed`

已具备：

- snapshots
- snapshot_entities
- rollback_to_snapshot()
- replay_patches_after_snapshot()
- graph_summary 观测

---

## 7. Docs Trust Assessment

### 值得信任的文档

`confirmed`

- `SKILL.md`
- `docs/superpowers/state/current-status.md`
- `docs/superpowers/specs/2026-04-05-runtime-retrieval-package-design.md`
- `docs/superpowers/specs/2026-04-05-patch-and-snapshot-design.md`
- `docs/superpowers/specs/2026-04-05-runtime-activation-and-flow-design.md`

这些文档和当前代码总体一致，只存在小幅日期漂移。

### 仍需警惕的地方

`inferred`

- 宿主适配层仍然主要是架构意图，不是完整实现。
- “完整多人社会模拟”仍远未完成。
- 激活传播仍是 bounded heuristic，不是成熟世界引擎。

---

## 8. 已测 vs 未测

### 已测

`confirmed`

- bootstrap / migrations / seeds
- narration/text_chat/email/file/directory 导入
- patch applier 核心分支
- runtime retrieval
- cache 命中 / 失效
- snapshot / rollback / replay
- dialogue loop
- identity duplicate merge
- scene lifecycle
- graph summary CLI

### 未充分测

`confirmed`

- retrieval cache 更复杂的 TTL / expires_at 场景
- branch resolution 的 candidate effect 是否真正改变 graph state
- 更多复杂 relation / conflict / ambiguous multi-hop 场景
- 更真实的对话宿主集成

### 未知

`unknown`

- 在更大规模数据下，当前 heuristic/budget/cache 组合是否仍稳定
- 当导入器来源变复杂时，current_states 与 branch 风险是否会过度膨胀

---

## 9. 当前最值得继续做的切片

建议按优先级推进：

### 切片 1：branch resolution 的 graph effect

目标：

- `resolve_local_branch` 不只改 branch/candidate 状态
- 如果 selected candidate 带 effect payload，应真正落到 graph state

原因：

- 当前歧义管理已经有 branch / candidates / risk 暴露
- 下一步最自然的是让“解决歧义”真的影响图谱

### 切片 2：retrieval cache TTL / metadata

目标：

- 用 `expires_at` 真正驱动缓存过期
- 记录 cache metadata，至少说明写入时间和 TTL

原因：

- 当前 cache 已可用，但还是最小版

### 切片 3：graph_summary 继续做工程观测

目标：

- branch candidate 状态分布更完整
- scene_active_relations / retrieval_cache / snapshots 的更明确统计

原因：

- 现在 `graph_summary.py` 已经是工程入口，继续增强收益很高

### 切片 4：抽更共用的 ingestion helper

目标：

- narration / text_chat / email 的事件壳、snapshot、patch 持久化进一步去重

原因：

- 现在已经有 `ingestion_helpers.py`
- 继续抽象能显著降低后续 importer 扩展成本

---

## 10. 恢复工作时的标准流程

新会话中的模型必须这样恢复：

1. 进入项目目录：

```bash
cd /Users/yellowpeachmac/mac-code/mac-code/we-together-skill
```

2. 先跑 fresh 全量测试：

```bash
.venv/bin/python -m pytest -q
```

预期：

```text
122 passed in ~3s
```

3. 先读：

- `SKILL.md`
- `docs/superpowers/state/current-status.md`
- 本文档

4. 再看最近 10 个 commit。

5. 选一个最小切片继续推进。

6. 严格 TDD：

- 先写失败测试
- 确认红灯
- 最小实现
- 相关子集回归
- 更新文档
- fresh 全量验证
- 只提交 `we-together-skill`

7. 提交命令固定：

```bash
git -C /Users/yellowpeachmac/mac-code/mac-code add we-together-skill
git -C /Users/yellowpeachmac/mac-code/mac-code commit -m "<message>"
```

---

## 11. 明确禁止事项

1. 不要碰上层仓库无关变更：
   - `.DS_Store`
   - `bilibili/`
2. 不要把这个项目改成新的独立 app 或 UI 项目。
3. 不要在没测试的情况下直接写实现。
4. 不要把未来设计说成已实现。
5. 不要 `git reset --hard`。
6. 不要改动宿主无关的目录。
7. 不要在没有 fresh 验证输出前宣称完成。

---

## 12. 给新会话中的 Codex 的最短启动提示

可以直接复制这段作为重启后的第一条任务提示：

> 你接手的项目是 `/Users/yellowpeachmac/mac-code/mac-code/we-together-skill`。
> 先读 `SKILL.md`、`docs/superpowers/state/current-status.md`、`docs/analysis/2026-04-14-self-handoff.md`。
> 再跑 `.venv/bin/python -m pytest -q`，预期 `122 passed`。
> 严格工程化推进：TDD、最小切片、文档同步、fresh 验证、只提交 `we-together-skill/`。
> 不要碰上层仓库的 `.DS_Store` 和 `bilibili/`。
> 当前优先方向：branch resolution 的 graph effect、retrieval cache TTL/metadata、graph_summary 进一步观测增强。
