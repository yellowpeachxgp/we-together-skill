# We Together 运行时检索包格式设计稿

## 1. 文档目标

本文档定义 `we together` 第一阶段在 Skill 运行时向模型提供的检索包格式。

重点回答：

- 运行时到底喂给模型什么
- 哪些信息属于必需项，哪些属于候选项
- 多人物场景如何压缩上下文
- latent 角色如何进入检索包但不直接发言

## 2. 设计原则

### 2.1 不把整张图谱喂给模型

运行时必须按场景裁剪。

### 2.2 检索包是派生视图

检索包不是数据库主对象，而是一次运行时组装结果。

### 2.3 结构化优先，文本补充

先给结构化字段，再给摘要文本。
不让自然语言长文成为唯一上下文。

## 3. 检索包总结构

第一阶段建议统一输出：

```text
RuntimeRetrievalPackage
  ├── scene_summary
  ├── environment_constraints
  ├── participants
  ├── active_relations
  ├── relevant_memories
  ├── current_states
  ├── activation_map
  ├── response_policy
  └── safety_and_budget
```

## 4. 必需部分

### 4.1 `scene_summary`

必须包含：

- `scene_id`
- `scene_type`
- `goal`
- `trigger_event`
- `group_context`
- `short_summary`

### 4.2 `environment_constraints`

必须包含：

- `location_scope`
- `channel_scope`
- `visibility_scope`
- `time_scope`
- `role_scope`
- `access_scope`
- `privacy_scope`
- `activation_barrier`

### 4.3 `participants`

必须包含：

- 当前参与人物
- 角色身份
- 与当前场景的直接关联原因

建议字段：

- `person_id`
- `display_name`
- `scene_role`
- `persona_summary`
- `style_summary`
- `speak_eligibility`

### 4.4 `response_policy`

必须包含：

- `mode`
- `primary_speaker`
- `supporting_speakers`
- `silenced_participants`
- `reason`

模式建议：

- `single_primary`
- `primary_plus_support`
- `multi_parallel`

## 5. 条件部分

### 5.1 `active_relations`

只放当前场景激活的关系，不放全量关系。

建议每条关系只保留：

- `relation_id`
- `participants`
- `core_type`
- `custom_label`
- `strength`
- `status`
- `short_summary`

### 5.2 `relevant_memories`

只放与当前 scene 高相关的记忆。

建议区分：

- `personal_memories`
- `shared_memories`

并限制总量。

### 5.3 `current_states`

只放当前场景真正起作用的状态：

- 人物状态
- 关系状态
- 群体状态
- 场景状态

### 5.4 `activation_map`

用于向模型解释：

- 谁被激活了
- 谁只是 latent
- 为什么某些角色被压住没有发言

建议字段：

- `person_id`
- `activation_score`
- `activation_state`
- `activation_reason_summary`

## 6. 检索预算

### 6.1 第一阶段建议预算

建议把检索包分成预算块，而不是无限扩张：

- scene summary：固定小预算
- participants：中预算
- active relations：中预算
- memories：中高预算
- states：中预算
- activation map：小预算

### 6.2 截断原则

优先级建议：

1. scene
2. participants
3. environment constraints
4. active relations
5. current states
6. relevant memories
7. activation map

如果预算不足，优先压缩 memory 数量，而不是丢 scene 与 participant。

## 7. 多人物场景压缩

### 7.1 角色卡压缩

对于每个参与人物，只给最短必要信息：

- 名字
- 当前场景身份
- 一句人物面摘要
- 一句风格摘要

### 7.2 关系压缩

每对相关关系最多保留一条主摘要，避免重复灌输。

### 7.3 记忆压缩

记忆优先保留：

- 与当前触发事件最相关
- 对当前关系张力最关键
- 能直接影响当前说话方式

## 8. latent 角色策略

### 8.1 latent 角色为什么要进检索包

因为他们虽然不发言，但可能影响：

- 当前气氛
- 发言边界
- 关系张力
- 谁敢说什么

### 8.2 latent 角色如何出现

第一阶段不应给 latent 角色完整发言位。
只在 `activation_map` 中留：

- 名字
- 激活分
- 不发言原因

## 9. 模型输入建议

第一阶段可以把检索包拆成两层输入：

### 9.1 结构化头部

放：

- scene
- participants
- response policy
- environment constraints

### 9.2 文本化上下文尾部

放：

- relation 摘要
- memory 摘要
- state 摘要
- activation 注释

这样比纯长文更可控。

## 10. 检索包缓存

对于同一个 `Scene + input_hash`，允许缓存检索包。

缓存失效条件建议：

- 新 event 写入
- active relations 变化
- current states 变化
- environment constraints 变化

## 11. 第一阶段最小实现要求

第一阶段至少要做到：

- 有固定检索包结构
- 有 scene summary
- 有 environment constraints
- 有 participants
- 有 response policy
- 有 active relations / memories / states 的裁剪逻辑
- 有 activation map

## 12. 结论

`we together` 运行时不应把数据库内容原样倾倒给模型。

它应被实现为：

> **一个以 Scene 为核心、以环境约束为边界、以激活传播结果为输入、并经过预算裁剪后的结构化运行时检索包。**
