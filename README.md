<div align="center">

# we together.skill

> *“Remember me ,when it's time to say goodbye.”*

> *“不是把一个人蒸馏成 Skill，而是把一群人蒸馏成 Skill。”*

<br>

把同事蒸馏成 Skill，只得到工作中的 TA。<br>
把自己蒸馏成 Skill，只得到自我镜像。<br>
把前任蒸馏成 Skill，只得到关系中的一面。<br>
但真实的人从来不是单点存在的。<br>

**`we together` 想做的是更完整的事：**<br>
导入多个人物、多种数据来源、多层关系链路，构建一个能够在 Skill 中运行、对话、演化的小型社会图谱。<br>

图恒宇，你在干什么！<br>
我只想……给丫丫一个完整的生命。<br>

[当前状态](#当前状态) · [设计目标](#设计目标) · [核心架构](#核心架构) · [规划中的数据来源](#规划中的数据来源) · [路线图](#路线图) · [参考项目与工具](#参考项目与工具)

</div>

---

## 当前状态

> 当前仓库处于 **设计基线阶段**，核心方向和工程约束已经确定，运行时与导入器尚未正式实现。

当前已经完成：

- 明确项目定位为 **Skill-first 的社会图谱系统**
- 确定第一阶段锚点场景为 **C：混合小社会**
- 确定采用 **统一社会图谱内核 + 领域投影** 架构
- 确定导入策略为 **默认全自动、自动入图谱**
- 确定演化策略为 **先写事件，再归并入图谱**
- 确定留痕策略为 **Git 式混合模型**
- 确定第一阶段只支持 **局部分支**，不支持整图分叉

当前核心设计文档：

- [`docs/superpowers/specs/2026-04-05-we-together-core-design.md`](docs/superpowers/specs/2026-04-05-we-together-core-design.md)
- [`docs/superpowers/state/current-status.md`](docs/superpowers/state/current-status.md)
- [`docs/superpowers/specs/2026-04-05-runtime-activation-and-flow-design.md`](docs/superpowers/specs/2026-04-05-runtime-activation-and-flow-design.md)
- [`docs/superpowers/specs/2026-04-05-unified-importer-contract.md`](docs/superpowers/specs/2026-04-05-unified-importer-contract.md)
- [`docs/superpowers/specs/2026-04-05-sqlite-schema-design.md`](docs/superpowers/specs/2026-04-05-sqlite-schema-design.md)
- [`docs/superpowers/specs/2026-04-05-patch-and-snapshot-design.md`](docs/superpowers/specs/2026-04-05-patch-and-snapshot-design.md)
- [`docs/superpowers/specs/2026-04-05-identity-fusion-strategy.md`](docs/superpowers/specs/2026-04-05-identity-fusion-strategy.md)
- [`docs/superpowers/specs/2026-04-05-runtime-retrieval-package-design.md`](docs/superpowers/specs/2026-04-05-runtime-retrieval-package-design.md)
- [`docs/superpowers/specs/2026-04-05-scene-and-environment-enums.md`](docs/superpowers/specs/2026-04-05-scene-and-environment-enums.md)

这意味着：

- 仓库现在适合被公开为 **项目基线与设计仓库**
- 但不应宣称所有采集器、图谱运行时、多人共演都已经完成

---

## 设计目标

`we together` 的目标不是做另一个“单人物蒸馏器”，而是做一个 **可运行、可演化、可追踪** 的社会图谱 Skill。

它最终希望具备以下能力：

- 从多种材料中导入多个人物
- 自动识别跨平台身份并融合成统一人物
- 构建人物之间的工作、生活、亲密、家庭、冲突、合作等多层关系
- 构建群体、场景、事件、记忆、状态等社会化对象
- 在 Skill 对话中支持多人共同回应
- 在新的对话和新导入数据中持续演化图谱
- 以留痕、快照、可逆合并的方式保持工程可控

一句话概括：

> **把“单个数字人格”升级为“一个有关系、有历史、有上下文的小型数字社会”。**

---

## 为什么要做这个

现有很多人物 Skill 都很强，但它们大多停留在“一个人”这一层。

问题在于，真实的人类社会并不是这样工作的：

- 一个人在工作里、亲密关系里、家庭里并不是同一种表现
- 人与人的关系会改变说话方式、决策方式、边界和冲突模式
- 很多记忆并不是“个人记忆”，而是“共享记忆”
- 很多状态并不是“这个人怎么了”，而是“这段关系怎么了”或者“这个群体现在怎么了”

所以 `we together` 不想把人做成孤立节点，而是想从一开始就把：

- 人物
- 关系
- 群体
- 场景
- 事件
- 记忆
- 当前状态

全部放在同一套图谱内核里。

---

## 核心架构

`we together` 当前的核心设计是五层：

### 1. 导入层

负责接入异构数据源，例如：

- 微信
- iMessage
- 飞书
- 钉钉
- Slack
- 邮件
- 图片 / 截图
- 用户口述 / 粘贴文本

### 2. 蒸馏层

负责把原始材料蒸馏为稳定结构，统一吸收以下已有思想：

- `Work`
- `Self Memory`
- `Persona`
- `Relationship Pattern`

### 3. 社会图谱内核

当前已确定的核心对象包括：

- `Person`
- `IdentityLink`
- `Relation`
- `Group`
- `Scene`
- `Event`
- `Memory`
- `State`

### 4. 运行层

负责 Skill 运行时的行为路由：

- 现在该由谁说话
- 哪些人物面应被激活
- 哪些关系、记忆、状态应参与当前回应
- 是否需要多人共同回应

### 5. 演化层

负责图谱的自动更新：

- 对话先写事件
- 再由事件推理 patch
- patch 归并到当前图谱
- 生成快照与历史留痕

---

## 核心设计原则

目前已经确定的工程原则如下：

- **统一图谱内核**：不做“工作系统”和“亲密系统”的双拼架构
- **默认自动化**：默认自动导入、自动匹配、自动入图谱
- **默认可逆**：激进自动融合允许，但必须可拆分、可回滚
- **事件优先**：所有演化先写事件，再改图谱
- **局部分支**：只对未决歧义做局部分支，不做整图分叉
- **摘要是派生视图**：自然语言摘要不能取代结构化主存储

---

## 规划中的数据来源

第一阶段规划支持的输入类型包括：

### 消息与聊天

- 微信聊天记录
- iMessage
- 飞书群聊 / 私聊
- 钉钉消息
- Slack 消息

### 文档与知识材料

- 飞书文档 / Wiki / 多维表格
- 钉钉文档 / 表格
- 邮件 `.eml` / `.mbox`
- Markdown / TXT / PDF

### 视觉与口述材料

- 图片 / 截图
- 直接口述
- 用户补充描述

### 关键区别

与单人物 Skill 不同，`we together` 在导入时不仅要“抽取内容”，还要做：

- **身份对齐**
- **人物融合**
- **关系推理**
- **共享记忆归属**
- **事件影响传播**

---

## 第一阶段路线图

### Phase 0：设计基线

- [x] 建立核心设计文档
- [x] 建立文档目录骨架
- [x] 确定核心实体与演化原则

### Phase 1：图谱内核

- [ ] 明确核心实体的具体存储格式
- [ ] 明确对象连接规则与更新流转
- [ ] 明确局部分支与快照模型
- [ ] 明确运行时检索契约

### Phase 2：统一导入器契约

- [ ] 定义 importer interface
- [ ] 复用参考项目中的现有导入器
- [ ] 统一归一化输出格式
- [ ] 引入身份匹配与人物融合

### Phase 3：Skill 运行时

- [ ] 支持单场景图谱装载
- [ ] 支持多人物回应路由
- [ ] 支持事件先行的自动演化
- [ ] 支持快照和局部分支落盘

### Phase 4：图谱增强

- [ ] 群体长期记忆
- [ ] 共享事件链
- [ ] 关系漂移建模
- [ ] 多源冲突归并

---

## 目前仓库结构

当前仓库重点是文档和设计基线：

```text
.
├── README.md
├── docs/
│   └── superpowers/
│       ├── README.md
│       ├── architecture/
│       ├── decisions/
│       ├── importers/
│       ├── specs/
│       │   └── 2026-04-05-we-together-core-design.md
│       ├── state/
│       │   └── current-status.md
│       └── vision/
└── .gitignore
```

后续实现会围绕这个文档结构推进，而不是把设计继续散落在聊天记录里。

---

## 参考项目与工具

`we together` 的方向并不是凭空提出的，它明确受以下项目启发，并计划复用其中可迁移的导入与蒸馏能力。

### 核心参考项目

- [`titanwings/colleague-skill`](https://github.com/titanwings/colleague-skill)
  - 提供了“工作能力 + 人物性格”的双层思路
  - 提供了飞书 / 钉钉 / Slack / 邮件等工作型导入能力

- [`notdog1998/yourself-skill`](https://github.com/notdog1998/yourself-skill)
  - 提供了“自我记忆 + 人格模型”的双层思路
  - 提供了微信、QQ、图片、社交内容、自我口述等个人型材料处理思路

- [`titanwings/ex-skill`](https://github.com/titanwings/ex-skill)
  - 提供了“关系人格建模”的强关系视角
  - 提供了微信 / iMessage / 关系行为模式 / 冲突链等强情境建模思路

### 可能会用到的数据提取参考工具

以下工具不是本项目代码的一部分，但很可能继续作为导入链路中的参考或兼容目标：

- [`LC044/WeChatMsg`](https://github.com/LC044/WeChatMsg)
  - 微信聊天记录导出

- [`xaoyaoo/PyWxDump`](https://github.com/xaoyaoo/PyWxDump)
  - 微信数据库解密与导出

- [`greyovo/留痕`](https://github.com/greyovo/留痕)
  - macOS 微信聊天记录导出

- `Feishu MCP / Feishu Open Platform`
  - 飞书文档、Wiki、消息、表格读取

- `DingTalk Open Platform`
  - 钉钉文档、用户、表格等导入

- `Slack SDK / Slack API`
  - Slack 消息与用户信息导入

### 参考原则

`we together` 会尽量复用这些项目和工具的“可迁移能力”，但不会直接把三套单人物架构粗暴拼接。  
本项目的重点是把它们统一到一个 **社会图谱内核** 之上。

---

## 项目状态说明

如果你现在来到这个仓库，请把它理解为：

- 一个已经有明确架构方向的项目
- 一个正在建立工程化基线的仓库
- 一个准备从“单人物 Skill”走向“多人社会图谱 Skill”的起点

但不要把它误解为：

- 所有功能已经实现
- 所有导入器已经接通
- 多人共演运行时已经完成

---

## 写在最后

“数字人格”这件事走到最后，真正难的从来不是让一个人说得像不像。  
真正难的是：

- 让一个人放到不同关系里依然像他自己
- 让几个人放在一起时，彼此之间的历史和张力都成立
- 让这个系统在新的对话里持续变化，而不是每次都从头演戏

`we together` 想做的，就是这一步。

不是一个人。

是**一群彼此有关联的人，作为一个可运行的数字社会，一起存在。**
