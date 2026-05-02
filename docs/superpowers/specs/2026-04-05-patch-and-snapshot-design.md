# We Together Patch 与 Snapshot 设计稿

## 1. 文档目标

本文档定义 `we together` 第一阶段的结构化变更模型：

- `Event` 如何产生 `Patch`
- `Patch` 如何作用于图谱主对象
- `Snapshot` 如何生成、回滚、重算
- 局部分支如何与 patch 和 snapshot 协同工作

本文档是以下设计稿的延续：

- `核心设计稿`
- `运行时激活与流转设计稿`
- `SQLite schema 设计稿`

## 2. 设计原则

### 2.1 Event 只记录发生，Patch 才记录修改

`Event` 的职责是记录“发生了什么”。
`Patch` 的职责是记录“系统因此决定改什么”。

两者不能混用。

### 2.2 Patch 必须是显式结构

Patch 不能是模糊自然语言说明，必须是结构化操作，能够被：

- 存储
- 重放
- 审计
- 回滚

### 2.3 Snapshot 是阶段性物化，不是替代历史

Snapshot 用来提升运行时效率和支持回滚，但不替代事件历史与 patch 历史。

### 2.4 回滚以 Snapshot 为主，重算以 Event + Patch 为主

第一阶段不追求完全任意粒度回滚。
优先支持：

- 基于 snapshot 的阶段性回退
- 基于 event + patch 的重算

## 3. 核心对象职责

### 3.1 Event

记录输入事实：

- 导入事实
- 对话事实
- latent/internal 运行时事实

不直接负责主对象修改。

### 3.2 Patch

记录结构化修改：

- 创建对象
- 更新对象
- 合并对象
- 拆分对象
- 建立连接
- 解除连接
- 创建局部分支
- 解决局部分支

### 3.3 Snapshot

记录某一时刻的稳定图谱视图：

- 当前包含哪些主对象版本
- 当前 graph state 的 hash
- 由哪些 event / patch 推导而来

### 3.4 LocalBranch

表示局部歧义的候选分叉：

- 不复制整图
- 只对局部对象范围生效

## 4. Patch 模型

### 4.1 Patch 的最小字段

第一阶段每个 patch 至少包含：

- `patch_id`
- `source_event_id`
- `target_type`
- `target_id`
- `operation`
- `payload_json`
- `confidence`
- `reason`
- `status`
- `created_at`
- `applied_at`

### 4.2 建议的操作类型

第一阶段建议支持以下操作：

- `create_entity`
- `update_entity`
- `merge_entities`
- `split_entity`
- `link_entities`
- `unlink_entities`
- `create_memory`
- `update_state`
- `create_local_branch`
- `resolve_local_branch`
- `mark_inactive`

### 4.3 目标对象范围

`target_type` 第一阶段允许取值：

- `person`
- `identity_link`
- `relation`
- `group`
- `scene`
- `event`
- `memory`
- `state`
- `local_branch`

### 4.4 Payload 规则

`payload_json` 必须满足：

- 可被机器解析
- 明确列出修改字段
- 不把整对象全文重复塞入
- 对于 merge / split，必须给出参与对象列表

例如：

- `update_entity`：字段变更列表
- `merge_entities`：源对象、目标对象、合并规则
- `split_entity`：原对象、新对象候选、拆分依据

## 5. Patch 生成流程

### 5.1 标准流程

统一流程：

1. 输入产生 `Event`
2. 事件进入 patch 推理层
3. 推理层根据规则和上下文生成一组 patch
4. patch 先落库
5. patch 再按顺序应用到 graph state
6. graph state 更新成功后标记 patch 为 `applied`

### 5.2 一次事件可生成多个 Patch

一个事件允许产生多个 patch，例如：

- 新增一个关系线索
- 强化一段已有关系
- 创建一个共享记忆
- 更新一条状态快照

### 5.3 一组 Patch 的应用顺序

推荐顺序：

1. `create_entity`
2. `link_entities`
3. `update_entity`
4. `create_memory`
5. `update_state`
6. `merge_entities / split_entity`
7. `create_local_branch / resolve_local_branch`

理由：

- 先有对象，后有连接
- 先稳定基础对象，再做复杂结构变更

## 6. Patch 应用规则

### 6.1 幂等性

第一阶段 patch 应尽量设计成可幂等：

- 重复应用不应造成数据倍增
- 允许通过唯一键或 hash 识别重复写入

### 6.2 可追溯性

任何主对象变更都必须能查到：

- 来自哪个 patch
- patch 来自哪个 event
- event 来自哪个 evidence 或哪轮对话

### 6.3 失败策略

如果 patch 应用失败：

- patch 状态标记为 `failed`
- 错误信息进入错误日志
- 不自动无痕跳过

### 6.4 部分成功策略

如果一组 patch 中只有部分成功：

- 必须记录成功与失败的边界
- 第一阶段建议优先采用“小事务组”
- 同一事件生成的 patch 可按逻辑块分批提交

## 7. Snapshot 模型

### 7.1 Snapshot 的作用

Snapshot 用于：

- 记录一个稳定阶段
- 提供阶段性回滚点
- 减少运行时从零重算的成本

### 7.2 Snapshot 最小字段

第一阶段每个 snapshot 至少包含：

- `snapshot_id`
- `based_on_snapshot_id`
- `trigger_event_id`
- `summary`
- `graph_hash`
- `created_at`

并配套 `snapshot_entities` 记录：

- 当前 snapshot 包含哪些主对象
- 每个对象的 hash 或版本标识

### 7.3 Snapshot 生成时机

第一阶段建议在以下场景生成 snapshot：

- 一次完整导入结束后
- 一轮多人对话结束后
- 一组重要 patch 应用后
- 局部分支被解决后

### 7.4 Snapshot 粒度

第一阶段使用“全局图谱快照 + 局部分支独立记录”的混合方式：

- 正常情况下做全局 snapshot
- 歧义处理只在 branch 层单独记录

## 8. 回滚与重算

### 8.1 回滚目标

第一阶段优先支持：

- 回滚到某个 snapshot
- 基于 snapshot 重新应用后续 patch

### 8.2 不建议的方式

第一阶段不建议：

- 直接手工改主对象表实现回滚
- 跳过 patch 历史做硬覆盖

### 8.3 回滚过程

标准流程：

1. 选择目标 snapshot
2. 恢复该 snapshot 对应的 graph state
3. 标记后续 patch 为未生效或进入重算队列
4. 按需要重放后续 event / patch

### 8.4 重算过程

重算以：

- `snapshot`
- `event`
- `patch`

三者共同驱动。

第一阶段允许采用：

- 从最近 snapshot 开始重放
- 不要求从系统初始点全量重算

## 9. Merge 与 Split 的特殊规则

### 9.1 Merge

`merge_entities` patch 必须明确：

- 哪些对象被合并
- 哪个对象是保留对象
- 别名、引用、关系、记忆如何迁移
- 合并后哪些对象进入 `merged` 状态

### 9.2 Split

`split_entity` patch 必须明确：

- 原对象
- 拆分出的新对象
- 哪些 identity / relation / memory / state 应重挂
- 原对象是否保留

### 9.3 Merge / Split 与 Branch 的关系

如果 merge 或 split 的置信度不足：

- 不应直接强改主图谱
- 应优先创建 `local_branch`

## 10. LocalBranch 与 Patch 的协作

### 10.1 创建局部分支

当系统遇到未决歧义时：

- 创建 `local_branch`
- 为 branch 写入多个 `branch_candidate`
- 同时记录 `create_local_branch` patch

### 10.2 解决局部分支

分支解决后：

- 写入 `resolve_local_branch` patch
- 把被选中的候选正式应用到主图谱
- 关闭其他候选

### 10.3 作用范围

局部分支第一阶段只允许作用于：

- `identity_link`
- `relation`
- `state`
- `person facet`

不允许整图分叉。

## 11. Patch 与 SQLite 的关系

### 11.1 Patch 是一等存储对象

Patch 不只是日志，而是可查询、可审计、可重放的结构化对象。

### 11.2 Patch 与主对象表解耦

主对象表保存当前状态。
Patch 表保存如何从过去走到现在。

### 11.3 Patch 与 Retrieval 的关系

运行时一般不直接全量读取 patch。
只有在以下情况才需要：

- 解释最近变化
- 构造 change-aware context
- 处理回滚或重算

## 12. 第一阶段最小实现要求

第一阶段至少应保证：

- 每个重要 event 都能生成 patch
- patch 落库后再应用
- patch 应用状态可追踪
- snapshot 可生成
- snapshot 可作为回滚点
- merge / split / local branch 有明确 patch 表达

## 13. 下一步建议

在本稿之后，建议继续撰写：

1. `Identity 融合策略设计稿`
2. `运行时检索包格式设计稿`
3. `数据库迁移与初始化方案`
4. `Scene 与环境参数枚举稿`

## 14. 结论

`we together` 第一阶段不能只靠 event 日志，也不能只靠当前主表。

它必须使用：

> **Event 记录事实，Patch 记录结构化改动，Snapshot 记录稳定阶段，三者共同构成可追溯、可回滚、可重算的社会图谱演化链。**
"},{"path":"docs/superpowers/state/current-status.md","content":"# 当前状态\n\n日期：2026-04-05\n\n当前已完成：\n\n- 明确项目定位为 Skill-first 的社会图谱系统\n- 选定第一阶段锚点场景为 `C：混合小社会`\n- 确定采用统一社会图谱内核，而不是工作/亲密双系统拼接\n- 确定关系模型为“核心维度固定 + 自定义扩展 + 自然语言摘要”\n- 确定导入策略为默认全自动、自动入图谱\n- 确定身份融合策略为激进自动融合，但必须可逆、可追溯\n- 确定演化策略为“先写事件，再归并入图谱”\n- 确定留痕模型为 Git 式混合结构\n- 确定第一阶段只支持局部分支，不支持整图分叉\n- 确定运行时采用“有界激活传播模型”\n- 确定环境参数采用“核心维度固定 + 自定义扩展”\n- 确定主存储采用 SQLite 与文件系统的混合模型\n- 确定 importer 采用“统一证据层 + 候选层”的输出契约\n- 确定 SQLite 为规范主对象与留痕对象的核心存储层\n- 确定 Event / Patch / Snapshot 为第一阶段的标准演化链\n\n当前主设计稿：\n\n- [2026-04-05-we-together-core-design.md](../specs/2026-04-05-we-together-core-design.md)\n- [2026-04-05-runtime-activation-and-flow-design.md](../specs/2026-04-05-runtime-activation-and-flow-design.md)\n- [2026-04-05-unified-importer-contract.md](../specs/2026-04-05-unified-importer-contract.md)\n- [2026-04-05-sqlite-schema-design.md](../specs/2026-04-05-sqlite-schema-design.md)\n- [2026-04-05-patch-and-snapshot-design.md](../specs/2026-04-05-patch-and-snapshot-design.md)\n\n下一步建议：\n\n- 定义 identity 融合策略\n- 定义运行时检索包格式\n- 定义 Scene 与环境参数枚举\n"}]}{Jsiianalysis to=functions.mcp__Github__push_files  彩神争霸平台json
