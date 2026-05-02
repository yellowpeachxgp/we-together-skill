# we-together vs LangMem

对比日期：2026-04-19。

## 定位对比

| 维度 | LangMem | we-together |
|------|--------|-------------|
| **所属** | LangChain 生态 | 独立 Skill runtime |
| **核心抽象** | Episodic / Semantic / Procedural memory | 社会 + 世界图谱（整合以上三种 + 关系 + 事件 + 物 + 地 + 项目）|
| **API** | `.put / .search` | SkillRuntime v1 + 4 类 plugin + REST (联邦) |
| **检索** | 向量 + 元数据过滤 | 向量 rerank + 有界激活传播 + 神经网格 multi-hop |
| **多 agent** | LangChain 的 multi-agent 框架 | 原生 PersonAgent + 互听/打断/私聊/转 dialogue_event |
| **时间** | 时间戳 | graph_clock 可模拟时间 + advance |
| **演化** | memory 条目级别 | 事件 → patch → snapshot → rollback + tick + drift |
| **不变式治理** | 未见 | 27 条不变式 + 55 条 ADR |

## 何时选 LangMem

- 已深度用 LangChain / LangGraph
- 想要与 LangChain 工具链无缝组合
- 需求偏**短期 memory + 检索**，不关心关系图谱

## 何时选 we-together

- 需要**关系 + 事件 + 世界**的统一模型
- 重视**工程化**（ADR + 不变式 + 测试基线）
- 需要**本地可审计**（图谱所有变更有留痕）
- 想要**多 agent + 梦循环 + 自修复**

## 可以共存吗

可以——写一个 `LangMemAdapter` plugin：
- we-together 作为主图谱
- LangMem 作为**特定 agent 的短时 memory 缓存**
- 两者通过 we-together 的 HookPlugin 同步

## 参考

- LangMem: https://github.com/langchain-ai/langmem
- 本文档为对比性，不代表 LangChain 团队观点。
