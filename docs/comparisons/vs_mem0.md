# we-together vs Mem0

**免责声明**：以下是基于**公开资料**的对比，Mem0 在快速演化，有出入请 PR 指正。对比日期：2026-04-19。

## 定位对比

| 维度 | Mem0 | we-together |
|------|------|-------------|
| **核心抽象** | 用户-级 "memory layer"（key-value + 向量）| 社会图谱 + 世界图谱（person / relation / event / memory / object / place / project）|
| **数据结构** | 主要是向量 + 文档 | SQLite 关系图谱（17 migrations）|
| **多 agent** | 通过 user_id 分 | 原生 PersonAgent + 互听 + 打断 + 私聊 |
| **时间模型** | 访问时间戳 | `graph_clock` 可 freeze / advance 模拟时间 |
| **关系建模** | 隐式（向量近邻）| 显式（relation + core_type + strength + drift）|
| **演化机制** | 写入为主 | tick + drift + decay + unmerge + dream_cycle |
| **宿主适配** | API 首选 | SkillRuntime v1（Claude Skills / OpenAI / MCP stdio）|
| **插件** | 有 LLM / vector store 插件 | 4 类 entry_points：importer / service / provider / hook |
| **不变式** | 未见公开清单 | 27 条明文不变式（ADR 0033/0039/0045/0052）|
| **遗忘** | 手动删除 | Ebbinghaus 曲线自动 archive ↔ reactivate 对称 |

## 何时选 Mem0

- 只需**给 LLM 加一层长期 memory**，不关心关系 / 社会结构
- 想要最快上手（SaaS 托管）
- 对向量检索延迟有极致需求

## 何时选 we-together

- 建模 **多人社会**（>= 3 人）长期互动
- 需要 **可回滚 / 可审计** 的图谱演化
- 希望 agent 有 **内在驱动力 + 梦循环 + 学习**
- 对 **schema 稳定性 / 不变式治理** 有要求
- 需要 **世界建模**（人 + 物 + 地 + 项目）而非纯 memory
- 想要一个**可插件化、可审计的本地 Skill**，而非 SaaS 黑箱

## 迁移成本

Mem0 → we-together：
- 用 `plugin_example_minimal` 写一个 Mem0 importer plugin
- 把 user_id 映射到 `person_id`
- memory 作为 `individual_memory` 导入

we-together → Mem0：
- 不支持（关系 / 世界 / tick 这些没法映射过去）

## 诚实的弱势

- **学习曲线更陡**：17 migrations + 27 不变式 + 52 ADR
- **CLI 更多**：bootstrap / seed / chat / simulate_week / fix_graph / ...
- **不是 SaaS**：自己装自己跑（也是优点）
- **向量后端**：当前 flat_python，真 sqlite-vec / FAISS 在 stub 阶段

## 参考

- Mem0: https://github.com/mem0ai/mem0
- 本文件属对比性文档，不代表 Mem0 团队观点。欢迎 PR 更新。
