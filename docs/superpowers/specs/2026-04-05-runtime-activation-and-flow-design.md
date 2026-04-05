# We Together 运行时激活与流转设计稿

## 1. 文档目标

本文档定义 `we together` 第一阶段的运行时规则，重点回答以下问题：

- 核心对象之间如何连接
- 导入或对话发生后，数据如何流转
- 多人物如何通过“激活传播”而不是固定路由参与当前场景
- 环境参数如何约束激活
- 内隐激活、显性发言、事件留痕之间如何区分
- 结构化对象与摘要文本分别落在哪里

本文档是对核心设计稿的运行时细化，不重复讨论项目愿景。

## 2. 适用范围

本文档只覆盖第一阶段：

- 混合小社会场景
- Skill-first 运行方式
- 局部分支
- SQLite + 文件系统混合存储

本文档暂不覆盖：

- 整图分叉
- 大规模社会模拟
- 完整 UI
- 全量导入器的具体实现细节

## 3. 运行时总原则

### 3.1 场景中心

一切运行时行为都以 `Scene` 为中心，而不是以 `Person` 或 `Group` 为中心。

运行时必须先回答：

- 当前是什么场景
- 当前场景允许谁被感知
- 当前场景允许谁被激活
- 当前场景允许谁真正发言

### 3.2 激活优先于发言

角色先被激活，再决定是否发言。

允许存在以下三层：

- 未激活
- 内隐激活
- 显性激活

### 3.3 环境约束先于关系传播

激活传播不能只看关系强弱。任何传播都必须先经过环境约束过滤。

### 3.4 事件优先于状态改写

无论是导入还是对话，先记录事件，再由事件推导 patch，再改写当前图谱状态。

## 4. 对象连接规则

### 4.1 主连接图

第一阶段规范主连接如下：

- `IdentityLink -> Person`
- `Relation -> Person`
- `Group -> Person`
- `Scene -> Person`
- `Scene -> Group`
- `Scene -> Relation`
- `Event -> Person`
- `Event -> Group`
- `Event -> Scene`
- `Event -> Relation`
- `Memory -> Event`
- `Memory -> Person`
- `Memory -> Relation`
- `State -> Person`
- `State -> Relation`
- `State -> Group`
- `State -> Scene`

### 4.2 禁止的错误建模

第一阶段明确禁止：

- 在 `Person` 内直接嵌入大段关系真相
- 在 `Memory` 中直接伪造没有来源事件的长期记忆
- 把 `Scene` 当成长期群体对象
- 把 `State` 当成长期稳定人格
- 让 importer 直接改写规范图谱对象

### 4.3 主责任边界

- `Person`：是谁
- `Relation`：彼此是什么关系
- `Group`：哪些人长期作为一个单位存在
- `Scene`：此刻处在什么互动现场
- `Event`：发生了什么
- `Memory`：什么被记住了且仍有影响
- `State`：现在处于什么状态

## 5. 写入流转

### 5.1 标准写入链路

第一阶段统一采用以下写入链路：

`导入/对话 -> Event -> Patch 推理 -> Graph State 更新 -> Snapshot`

### 5.2 导入流

导入流按以下步骤执行：

1. importer 产出原始证据和候选对象
2. 统一归一化层把候选对象转成：
   - `identity_candidates`
   - `event_candidates`
   - `facet_candidates`
   - `relation_clues`
   - `group_clues`
3. 身份融合模块做自动匹配和人物合并
4. 生成导入事件 `import_event`
5. 由导入事件推理结构化 patch
6. patch 写入当前图谱
7. 记录快照

### 5.3 对话流

对话流按以下步骤执行：

1. 识别当前场景
2. 构建运行时检索包
3. 完成多人物响应
4. 把本轮过程写成 `dialogue_event`
5. 根据 `dialogue_event` 推理：
   - 新关系线索
   - 状态变化
   - 记忆强化或新增
   - 局部分支候选
6. patch 写入当前图谱
7. 视条件生成快照

### 5.4 Patch 结构

第一阶段的 patch 应是显式结构，而不是自由文本。

建议 patch 类型：

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

每个 patch 必须带：

- `patch_id`
- `source_event_id`
- `target_type`
- `target_id`
- `operation`
- `payload`
- `confidence`
- `reason`
- `created_at`

## 6. 读取流转

### 6.1 标准读取链路

统一读取链路如下：

`Scene -> Participants -> Active Relations -> Relevant Memories -> Current States -> Response Assembly`

### 6.2 读取步骤

1. 先确定当前 `Scene`
2. 从 `Scene` 找到初始参与者和环境参数
3. 在环境参数允许的范围内做激活传播
4. 取传播后达到阈值的关系、记忆、状态
5. 生成运行时检索包
6. 决定谁显性发言、谁只保持内隐激活
7. 生成最终输出

### 6.3 检索包组成

每次调用 Skill 时，只组装以下内容：

- `scene_summary`
- `participants`
- `active_relations`
- `relevant_memories`
- `current_states`
- `response_policy`

运行时禁止：

- 全量注入整张图谱
- 把所有关系和记忆无差别送入模型

## 7. 激活传播模型

### 7.1 设计目标

第一阶段不采用固定主角色路由，也不采用无边界自由群聊。采用“有界激活传播模型”。

### 7.2 激活阶段

运行时将角色分成三层：

- `inactive`：未激活
- `latent`：已被触发，但不一定发言
- `explicit`：进入最终可见输出

### 7.3 基础流程

1. `Scene` 生成一批种子角色
2. 种子角色沿以下链路传播激活：
   - `Relation`
   - `Memory`
   - `Event`
   - `Group`
3. 每次传播都计算激活分数
4. 激活分数经过衰减和环境过滤
5. 达到阈值的角色进入 `latent`
6. 进一步满足发言条件的角色进入 `explicit`

### 7.4 核心参数

第一阶段建议固定以下核心参数，并允许后续扩展：

- `seed_count`
- `activation_budget`
- `propagation_depth`
- `relation_weight`
- `memory_weight`
- `event_weight`
- `group_weight`
- `decay_rate`
- `speak_threshold`
- `silent_threshold`

### 7.5 工程规则

- 激活预算有限
- 传播层级有限
- 角色可以被激活但保持沉默
- 没有通过环境约束的角色不得进入激活链

## 8. 环境参数模型

### 8.1 设计原则

环境参数采用“核心维度固定 + 自定义扩展”。

### 8.2 第一阶段固定核心维度

- `location_scope`
- `channel_scope`
- `visibility_scope`
- `time_scope`
- `role_scope`
- `access_scope`
- `privacy_scope`
- `activation_barrier`

### 8.3 作用方式

环境参数在激活传播前先做过滤，用来判断：

- 角色是否可见
- 角色是否可达
- 角色是否具备介入资格
- 角色当前哪一面身份有效

### 8.4 硬规则

任何角色的激活必须同时满足：

- 图谱相关性
- 场景可达性

只满足其一，不得进入显性激活。

## 9. 多人物发言收敛

### 9.1 目标

第一阶段必须避免“人人都说话”的假热闹。

### 9.2 发言模式

建议保留三种模式：

- `single_primary`
- `primary_plus_support`
- `multi_parallel`

### 9.3 默认策略

- 私聊场景：默认 `single_primary`
- 双人强关系场景：默认 `primary_plus_support`
- 群体讨论场景：默认 `primary_plus_support`
- 明确群体讨论型场景：允许 `multi_parallel`

### 9.4 发言原则

硬规则：

> 能沉默的人就让他沉默。

角色即使被激活，也不必发言。只有达到显性阈值并满足当前场景发言资格时才输出。

## 10. 内隐事件与显性事件

### 10.1 为什么需要内隐事件

在一个社会图谱里，很多角色会被牵动，但不一定说话。

这些“被牵动”本身也有价值，不能全部丢弃。

### 10.2 第一阶段事件分类

- `visible_event`
  - 用户可见对话或导入结果
- `latent_event`
  - 角色被激活但未发言
- `internal_event`
  - 系统内部推理、分支建立、合并决策、状态漂移记录

### 10.3 规则

- `visible_event` 可参与用户可见历史
- `latent_event` 和 `internal_event` 只参与图谱演化，不直接混入用户可见对话流

## 11. SQLite 与文件系统分工

### 11.1 SQLite 负责

第一阶段 SQLite 负责规范主对象和结构化留痕：

- `Person`
- `IdentityLink`
- `Relation`
- `Group`
- `Scene`
- `Event`
- `Memory`
- `State`
- `Patch`
- `Snapshot`
- `LocalBranch`

### 11.2 文件系统负责

文件系统负责长文本和工程文档：

- README
- 设计文档
- 导入器说明
- 派生摘要
- 原始材料归档
- 运行时组合包模板

### 11.3 主从规则

硬规则：

- SQLite 中的结构化字段是规范真相
- 文件中的摘要和长文本是派生视图或原始材料
- 派生视图不能反向覆盖规范真相，除非通过新的 `Event` 和 `Patch`

## 12. 第一阶段的最小实现约束

第一阶段至少要满足：

- 有规范主对象
- 有事件先行写入链
- 有 patch 层
- 有环境参数过滤
- 有激活传播机制
- 有 latent / explicit 区分
- 有 SQLite 与文件分层

第一阶段可以先不做：

- 整图复杂检索优化
- 大规模并发多人内部自发对话
- 全量导入器打通
- 图谱世界线级 branch

## 13. 下一步建议

在本文档之后，建议继续写以下文档：

1. `SQLite schema 设计稿`
2. `统一 importer 契约`
3. `Patch 与 Snapshot 设计稿`
4. `运行时检索包格式设计稿`

## 14. 结论

`we together` 第一阶段的运行时不应被实现为：

- 固定人物路由器
- 自由无界群聊器
- 纯 prompt 拼接器

它应被实现为：

> **一个以 Scene 为中心、受环境约束、通过有界激活传播驱动多人参与，并以 Event -> Patch -> Graph State 方式持续演化的社会图谱 Skill。**
