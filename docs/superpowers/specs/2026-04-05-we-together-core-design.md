# We Together 核心设计稿

## 1. 项目目标

`we together` 是一个以 Skill 为运行载体的社会图谱系统，用来构建并运行一个小型数字社会。

它不是单人物 Skill 生成器，而是一个能够：

- 从异构数据源导入多个人物
- 对跨平台身份进行自动对齐与融合
- 构建人物、关系、群体、记忆、事件、状态等结构化对象
- 在 Skill 运行时支持多人互动与共演
- 在对话和新数据导入后自动演化图谱

第一阶段的设计锚点为 **C：混合小社会**：

- 4 到 10 个人
- 同时包含同事关系、亲密关系、私人关系
- 场景同时覆盖工作群、私聊、共享历史和生活上下文

## 2. 非目标

第一阶段不以以下内容为目标：

- 建模一个无限扩张的大型社会
- 支持整张图谱的全局分叉
- 只依赖自由文本作为唯一真相
- 在正常导入流程中要求用户手工逐项确认
- 在图谱内核未稳定前把所有导入器都做到生产级完整度

## 3. 设计原则

### 3.1 工程优先

系统必须是一个结构化运行时，而不是松散的 Prompt 拼接。自然语言摘要只能是派生视图，不能充当主存储。

### 3.2 统一社会图谱内核

系统只允许有一个统一图谱内核。工作面、生活面、亲密面、表达面不是四套系统，而是同一人物和同一关系在不同场景下的不同投影。

### 3.3 默认自动化

导入、身份匹配、人物融合、关系生成、图谱更新默认自动运行。正常使用流程不应要求用户手工审阅每一步。

### 3.4 默认可逆

允许激进的自动匹配与自动合并，但所有合并、推理关系、状态变化都必须可追踪、可拆分、可回滚。

### 3.5 事件优先于直接改写

导入动作和对话动作应先写入事件，再由事件驱动图谱改写，而不是直接无痕修改人物或关系本体。

### 3.6 歧义局部化

人的复杂性和自相矛盾应在同一个人物模型中通过场景触发和多面特征表达。分支只用于未决歧义，不用于表达人格多面性。

## 4. 总体架构

系统由五层组成：

### 4.1 导入层

负责接入异构数据源：

- 微信
- iMessage
- 飞书
- 钉钉
- Slack
- 邮件
- 图片与截图
- 用户直接粘贴或口述的文本

该层尽可能复用 `colleague-skill`、`yourself-skill`、`ex-skill` 中已有的采集器与解析器能力，但必须封装到统一导入接口下。

### 4.2 蒸馏层

负责从导入材料中抽取稳定结构：

- 人物特征
- 关系信号
- 群体信号
- 事件候选
- 记忆候选

该层复用并统一三类已有抽象：

- `Work`
- `Self Memory`
- `Persona`
- `Relationship Pattern`

### 4.3 社会图谱内核

该层是系统的规范主模型，包含：

- `Person`
- `IdentityLink`
- `Relation`
- `Group`
- `Scene`
- `Event`
- `Memory`
- `State`

### 4.4 运行层

负责 Skill 运行时行为：

- 决定谁应当回应
- 决定当前场景激活哪些人物面和关系面
- 检索相关记忆、关系、状态、事件
- 支持单人回应与多人共演

### 4.5 演化层

负责图谱自动演化：

- 记录新的对话事件
- 推理关系变化和新记忆
- 更新状态快照
- 生成快照与历史留痕

## 5. 核心术语

### 5.1 Person

稳定的人物本体，表示“这个人是谁”。

### 5.2 IdentityLink

跨来源身份映射对象，表示“外部账号、别名、称呼如何映射到同一个人物”。

### 5.3 Relation

结构化关系对象，表示“这些人彼此是什么关系”。

### 5.4 Group

长期存在的社会单元，表示“这群人作为一个单位长期存在”。

### 5.5 Scene

具体互动现场，表示“这些人此刻处在什么社交上下文中”。

### 5.6 Event

离散发生的一件事，表示“发生了什么”，也是系统主要变化来源。

### 5.7 Memory

由事件和证据蒸馏出的记忆对象，表示“什么被记住了，而且仍有影响”。

### 5.8 State

当前动态状态快照，表示“现在处于什么状态”。

## 6. 核心实体模型

### 6.1 Person

`Person` 用于存储稳定或半稳定的人物信息。

职责：

- 身份锚点
- 稳定人格画像
- 工作面
- 生活面
- 表达风格面
- 长期习惯、价值观、边界
- 来源与版本引用

明确不应直接存储：

- 原始外部账号身份
- 某个场景下的临时状态
- 具体关系记录的大段文本

建议字段：

- `person_id`
- `primary_name`
- `aliases`
- `role_tags`
- `persona_facets`
- `work_facets`
- `life_facets`
- `style_facets`
- `boundary_facets`
- `evidence_refs`
- `created_at`
- `updated_at`

### 6.2 IdentityLink

`IdentityLink` 用于把外部身份映射到规范人物。

职责：

- 平台身份到规范人物的映射
- 匹配依据保留
- 后续拆分或重对齐支持

建议字段：

- `identity_id`
- `platform`
- `external_id`
- `display_names`
- `contact_fields`
- `linked_person_id`
- `match_method`
- `confidence`
- `is_user_confirmed`
- `conflict_flags`
- `evidence_refs`

匹配分层：

- 强匹配：邮箱、手机号、稳定平台 ID、凭证级身份
- 中匹配：姓名、昵称、组织角色、稳定别名
- 弱匹配：风格相似、共现关系、上下文推理

硬规则：

允许系统在自动模式下基于弱证据进行激进候选融合，但底层映射必须保留证据，并且必须支持后续拆分。

### 6.3 Relation

`Relation` 是规范关系对象，不能退化成 `Person` 内的一个附属字段。

职责：

- 描述关系类型与结构
- 记录方向性与强度
- 记录歧义、冲突与变化
- 承载关系上的领域特征

建议字段：

- `relation_id`
- `participant_ids`
- `core_type`
- `custom_label`
- `summary`
- `directionality`
- `strength`
- `stability`
- `visibility`
- `facets`
- `status`
- `time_range`
- `evidence_refs`
- `change_log_refs`

`core_type` 应有固定主域但允许扩展，例如：

- `work`
- `family`
- `friendship`
- `intimacy`
- `authority`
- `care`
- `conflict`
- `collaboration`

关键规则：

同一组人物之间允许同时存在多条关系对象。

### 6.4 Group

`Group` 用于建模长期存在的群体单位。

职责：

- 成员集合
- 群内角色结构
- 群体规范
- 群体历史
- 群体共享记忆入口

建议字段：

- `group_id`
- `group_type`
- `name`
- `member_ids`
- `member_roles`
- `norms`
- `shared_memory_refs`
- `event_refs`
- `active_scene_templates`

### 6.5 Scene

`Scene` 用于建模当前运行时的互动现场。

职责：

- 定义当前参与者
- 定义可见信息范围
- 定义行为路由
- 决定当前应优先激活哪些人物面和关系面

建议字段：

- `scene_id`
- `scene_type`
- `participant_ids`
- `group_id`
- `trigger_event_id`
- `active_relation_ids`
- `active_memory_refs`
- `visibility_scope`
- `response_policy`
- `scene_state_ref`

关键区分：

`Group` 是长期单元，`Scene` 是运行时上下文。

### 6.6 Event

`Event` 是系统的主变化源。

职责：

- 记录发生的事情
- 记录参与者与上下文
- 保留原始证据引用
- 作为记忆、关系漂移、状态变化的上游输入

建议字段：

- `event_id`
- `event_type`
- `participant_ids`
- `group_id`
- `scene_id`
- `timestamp`
- `raw_evidence_refs`
- `structured_summary`
- `impact_targets`
- `impact_patch_refs`

关键规则：

系统应优先追加事件，而不是无事件痕迹地直接修改稳定对象。

### 6.7 Memory

`Memory` 是蒸馏后的记忆对象，不是原始聊天记录的另一种存法。

记忆类型建议先分为：

- 个体记忆
- 共享记忆

建议字段：

- `memory_id`
- `memory_type`
- `owner_ids`
- `summary`
- `source_event_ids`
- `emotional_tone`
- `confidence`
- `relevance_score`
- `active_relation_ids`
- `is_shared`

### 6.8 State

`State` 用于存储当前动态快照。

范围示例：

- 某个人当前的情绪或防御状态
- 某段关系当前的紧张度
- 某个群体当前的氛围
- 某个场景当前的开放度

建议字段：

- `state_id`
- `scope_type`
- `scope_id`
- `state_type`
- `value`
- `confidence`
- `source_event_ids`
- `updated_at`
- `decay_policy`
- `is_inferred`

关键规则：

`State` 是当前快照，不是长期真相。

## 7. 连接规则

### 7.1 规范连接图

主要允许连接如下：

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

### 7.2 主更新链路

主更新流程：

`导入/对话 -> Event -> patch 推理 -> 图谱状态改写 -> 快照`

主读取流程：

`Scene -> 参与者 -> 激活关系 -> 相关记忆 -> 当前状态 -> 响应组装`

### 7.3 派生视图规则

摘要、Prompt 包、检索包都只能是派生视图，不能替代规范主对象。

## 8. 导入与身份融合

### 8.1 导入器策略

系统应尽可能复用三个参考项目中的采集器能力，但导入后必须统一归一化为：

- 原始证据对象
- 候选身份对象
- 候选事件对象
- 候选人物面
- 候选关系线索

### 8.2 自动身份融合

第一阶段默认采用激进自动融合。

原因：

- Skill 必须是全自动的
- 初次测试时图谱如果碎裂，将无法验证系统价值
- 用户不应在正常流程中反复确认“是不是同一个人”

但激进融合必须同时满足：

- 合并可逆
- 证据留痕
- 置信度分层
- 后续可拆分

### 8.3 合并落库规则

系统在导入阶段和运行时都允许自动合并人物，但必须记录：

- 原始身份记录
- 合并依据
- 合并置信度
- 合并时间
- 是否可拆分

## 9. 运行时与自动演化

### 9.1 Skill 运行时能力

运行时必须能够：

- 决定当前该由一个人还是多个人回应
- 根据当前场景选择正确的人物面投影
- 在必要时组合工作面、生活面、亲密面和表达面
- 检索相关记忆、关系、状态与近期事件
- 生成社会一致性的回应

### 9.2 演化策略

系统采用“事件先行”的自动演化模式：

1. 把对话或导入写成原始或半结构化事件
2. 从事件中推理图谱 patch
3. 把 patch 应用到当前 graph state
4. 更新相关状态快照
5. 派生或强化记忆
6. 达到条件后生成快照

### 9.3 歧义处理规则

人的复杂性和矛盾性应通过同一人物模型中的多面特征与场景触发机制表达。

分支只用于未决歧义，例如：

- 身份是否应合并
- 关系应如何解释
- 某次事件应如何归类
- 某个状态应如何赋值

## 10. 留痕、快照与局部分支

### 10.1 Git 式混合模型

第一阶段采用 Git 式混合留痕模型：

- `event journal`：追加式历史流
- `graph state`：当前可运行图谱
- `snapshot/commit`：patch 应用后的稳定快照

### 10.2 为什么不做纯事件溯源

纯事件溯源在第一阶段会让 Skill 运行过重。

### 10.3 为什么不做直接改图谱不留史

直接改图谱而不保留事件历史，会让后续回滚、重算、纠错都变得脆弱。

### 10.4 局部分支

第一阶段只支持局部分支，不支持整图分叉。

允许分支的范围：

- `IdentityLink`
- `Relation`
- `State`
- 特定 `Person facet`

第一阶段不做：

- 整图 branch tree
- 竞争世界线副本

## 11. 仓库文档结构建议

项目必须从第一天起维持严格工程化文档。

建议目录结构：

```text
docs/
  superpowers/
    specs/
    architecture/
    decisions/
    state/
    importers/
    vision/
```

建议职责如下：

- `vision/`：项目目标、边界、术语
- `architecture/`：稳定架构说明
- `decisions/`：关键设计决策历史
- `state/`：当前状态、下一步、未决问题
- `importers/`：导入器契约和各来源说明
- `specs/`：具体实现设计稿

## 12. 第一阶段实现范围

第一阶段优先建设图谱内核和文档骨架，而不是追求导入器全面完成。

第一阶段应包括：

- 规范核心 schema
- 统一导入器契约
- 身份融合模型
- 事件优先的自动演化模型
- 局部分支模型
- 运行时检索契约
- 仓库文档骨架

第一阶段暂不包括：

- 所有导入器的生产级完善
- 独立应用或完整 UI
- 整图分支管理
- 大规模社会仿真

## 13. 未决问题

以下问题留给下一份 spec 或 ADR：

- 规范对象的具体存储格式
- snapshot 的生成时机与重算策略
- 运行时检索包的数据格式
- patch 推理策略细节
- 导入器归一化契约细节
- 多人场景中的说话者路由策略

## 14. 结论

项目应先设计并实现统一社会图谱内核，同时把三个参考项目中的导入能力封装到统一导入契约下。

这样既能保留它们的优点，又不会继承它们“单人物 Skill 架构”的根本限制。
