# We Together 统一导入器契约

## 1. 文档目标

本文档定义 `we together` 第一阶段的统一导入器契约。

目标不是说明某个平台如何抓取数据，而是统一回答以下问题：

- 导入器的边界是什么
- 每个导入器必须产出哪些中间对象
- 原始证据、身份候选、事件候选、关系线索如何统一建模
- 导入器与图谱写入层之间如何解耦
- 哪些能力来自参考项目，哪些能力属于 `we together` 新增部分

## 2. 适用范围

本文档适用于第一阶段所有输入源，包括但不限于：

- 微信
- iMessage
- 飞书
- 钉钉
- Slack
- 邮件
- 文档与表格
- 图片与截图
- 用户直接口述或粘贴文本

本文档不定义：

- 平台级抓取细节
- OCR 细节
- SQLite 表结构细节
- 事件 patch 推理细节

这些内容将在后续文档中分别定义。

## 3. 设计原则

### 3.1 平台无关

导入器必须先把平台世界翻译成统一中间层，而不是直接把平台字段写进图谱主对象。

### 3.2 证据优先

导入器首先产出原始证据及其来源信息。所有候选对象都必须可回指到原始证据。

### 3.3 候选优先于真相

导入器只产生候选身份、候选事件、候选关系线索和候选人物面，不直接写最终图谱真相。

### 3.4 自动化优先

导入流程默认全自动运行，不要求用户手工逐条确认。

### 3.5 可逆与可追溯

导入器即使做激进候选推理，也必须保留：

- 证据
- 来源
- 置信度
- 匹配方法

## 4. 导入器职责边界

每个 importer 只负责四类事情：

### 4.1 采集原始材料

导入器负责从来源中取得原始内容，例如：

- 消息记录
- 文档正文
- 邮件正文
- 表格内容
- 图片文本或图像描述
- 用户口述文本

### 4.2 提取候选身份

导入器负责识别与人物相关的外部身份信息，例如：

- 平台账号 ID
- 昵称
- 姓名
- 别名
- 手机号
- 邮箱
- handle
- 群内称呼

### 4.3 提取候选事件与关系线索

导入器负责识别可结构化的社会互动线索，例如：

- 谁在什么时候说了什么
- 谁与谁在什么场景中共现
- 哪些内容像合作、冲突、告白、入职、分手、安慰、共同活动
- 哪些内容提示某个群体结构或角色关系

### 4.4 产出统一中间结果

导入器必须把结果输出为统一中间层对象，而不是直接改写：

- `Person`
- `Relation`
- `Group`
- `Memory`
- `State`

## 5. 统一中间层对象

### 5.1 RawEvidence

`RawEvidence` 是导入器产出的第一等对象。

职责：

- 保留原始内容
- 保留来源路径与来源平台
- 保留时间、上下文、采集方式
- 作为所有后续候选对象的证据来源

建议字段：

- `evidence_id`
- `import_job_id`
- `source_type`
- `source_platform`
- `source_locator`
- `content_type`
- `raw_content`
- `normalized_text`
- `timestamp`
- `participants_hint`
- `metadata`

### 5.2 IdentityCandidate

`IdentityCandidate` 表示导入器提取出的身份候选。

职责：

- 标记原始世界里的账号、名字、别名、称呼
- 供身份融合模块后续自动合并或拆分

建议字段：

- `candidate_id`
- `evidence_id`
- `platform`
- `external_id`
- `display_name`
- `aliases`
- `contact_fields`
- `org_fields`
- `match_hints`
- `confidence`

### 5.3 EventCandidate

`EventCandidate` 表示导入器识别出的潜在事件。

职责：

- 从原始材料中抽取结构化交互单元
- 为后续 `Event` 写入提供候选基础

建议字段：

- `candidate_id`
- `evidence_id`
- `event_type`
- `actor_candidates`
- `target_candidates`
- `group_candidates`
- `scene_hint`
- `time_hint`
- `summary`
- `confidence`

### 5.4 FacetCandidate

`FacetCandidate` 表示人物面的候选信息。

可覆盖的面包括：

- `work`
- `life`
- `persona`
- `style`
- `boundary`
- `relationship_pattern`

建议字段：

- `candidate_id`
- `evidence_id`
- `target_identity_candidates`
- `facet_type`
- `facet_key`
- `facet_value`
- `confidence`
- `reason`

### 5.5 RelationClue

`RelationClue` 表示导入器发现的关系线索，而不是最终关系对象。

职责：

- 提供关系候选
- 提供关系强弱、方向、边界、情绪色彩等线索

建议字段：

- `clue_id`
- `evidence_id`
- `participant_candidates`
- `core_type_hint`
- `custom_label_hint`
- `directionality_hint`
- `strength_hint`
- `stability_hint`
- `summary`
- `confidence`

### 5.6 GroupClue

`GroupClue` 表示导入器发现的群体线索。

职责：

- 标记潜在长期群体
- 标记成员与角色结构

建议字段：

- `clue_id`
- `evidence_id`
- `group_type_hint`
- `group_name_hint`
- `member_candidates`
- `role_hints`
- `norm_hints`
- `confidence`

## 6. 统一导入结果结构

每个 importer 最终都必须输出如下结构：

```text
ImportResult
  ├── raw_evidences
  ├── identity_candidates
  ├── event_candidates
  ├── facet_candidates
  ├── relation_clues
  ├── group_clues
  ├── warnings
  └── stats
```

其中：

- `raw_evidences` 是必需项
- 其他项允许为空，但必须存在字段

## 7. 导入器不得做的事情

导入器明确不得：

- 直接创建最终 `Person`
- 直接创建最终 `Relation`
- 直接写入最终 `Memory`
- 直接改写运行时 `State`
- 跳过证据层直接输出真相断言

导入器可以做激进候选推理，但不能越权做最终图谱裁决。

## 8. 导入作业模型

为了保证留痕和可重放，第一阶段建议引入 `ImportJob`。

### 8.1 ImportJob 职责

- 标记一次导入动作
- 聚合同一批 evidence 和候选对象
- 为后续重算提供边界

建议字段：

- `import_job_id`
- `source_type`
- `source_platform`
- `started_at`
- `finished_at`
- `operator`
- `status`
- `stats`
- `error_log`

### 8.2 ImportSession

如果一次用户操作中混用了多种来源，可以再上层引入 `ImportSession` 聚合同一轮导入过程。

第一阶段可选，不强制。

## 9. 身份融合前的统一处理

导入器输出中间层后，统一进入“归一化与身份融合前处理”阶段。

该阶段负责：

- 去重证据
- 清理无效候选
- 把同一 evidence 下的角色标注统一化
- 提供强、中、弱匹配提示
- 生成后续自动融合输入

导入器本身不直接实现最终身份融合。

## 10. 来源类型与优先级

### 10.1 第一阶段推荐优先级

优先接入顺序建议如下：

1. 文本型聊天记录
2. 工作型文档与表格
3. 邮件
4. 图片与截图
5. 口述输入

原因：

- 聊天和文档最容易形成事件链
- 邮件适合补充正式表达与角色边界
- 图片与截图价值高，但归一化成本更高
- 口述灵活，但主观性强，应作为补充层

### 10.2 参考项目复用映射

#### 来源于 `colleague-skill`

优先复用的能力：

- 飞书自动采集
- 钉钉自动采集
- Slack 自动采集
- 邮件解析
- 工作型人物面抽取思路

#### 来源于 `yourself-skill`

优先复用的能力：

- 微信 / QQ / 社交文本输入思路
- 自我记忆与生活方式面抽取思路
- 图片元信息处理思路

#### 来源于 `ex-skill`

优先复用的能力：

- 微信 / iMessage 聊天提取
- 关系行为模式抽取
- 冲突链与情感事件识别思路

## 11. 置信度约束

统一要求所有候选对象都必须带 `confidence`。

第一阶段可采用三档：

- `high`
- `medium`
- `low`

或对应的数值型实现。

### 11.1 高置信候选

可直接进入后续自动融合和 patch 推理流程。

### 11.2 中置信候选

可进入自动流程，但应在后续 patch 与 snapshot 中保留更强的可逆性。

### 11.3 低置信候选

可以保留，但不应直接推动强结构结论，优先作为局部分支或弱线索。

## 12. 文件与存储分工

### 12.1 SQLite 中应保存

- `ImportJob`
- `RawEvidence` 的索引信息
- 候选对象的结构化索引
- 后续融合结果的引用关系

### 12.2 文件系统中应保存

- 原始导入材料副本
- 中间导出文本
- OCR 结果文本
- 导入日志文件
- 导入说明文档

### 12.3 硬规则

原始材料可以在文件系统中存全文，但 SQLite 中必须至少存索引、定位信息和引用关系，保证后续重放可行。

## 13. 错误与警告

每个 importer 必须返回：

- `warnings`
- `stats`

示例 warning：

- 数据来源不完整
- OCR 结果质量低
- 身份候选冲突过多
- 时间戳缺失
- 渠道信息不可用

这些 warning 不应阻断导入，但必须留痕。

## 14. 第一阶段最小实现要求

第一阶段统一导入器契约至少要做到：

- 有统一的 `ImportResult`
- 有统一的证据层
- 有统一的候选层
- 有 `ImportJob`
- 有来源置信度字段
- 有 warning 和 stats
- 不允许 importer 越权直接写规范图谱真相

## 15. 下一步建议

在本文档之后，建议继续撰写：

1. `SQLite schema 设计稿`
2. `Patch 与 Snapshot 设计稿`
3. `Identity 融合策略设计稿`
4. `运行时检索包格式设计稿`

## 16. 结论

`we together` 的 importer 不应被实现为一组彼此孤立的平台脚本。

它们应被实现为：

> **一组平台各异、但统一输出为证据层与候选层对象的标准化入口，让导入器负责“翻译世界”，而把“决定真相”交给统一图谱内核。**
