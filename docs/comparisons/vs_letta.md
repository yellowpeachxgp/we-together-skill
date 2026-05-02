# we-together vs Letta (MemGPT)

对比日期：2026-04-19。

## 定位对比

| 维度 | Letta / MemGPT | we-together |
|------|---------------|-------------|
| **核心抽象** | agent（持久 memory + tools）| 社会 + 世界图谱 + 多 agent 共存 |
| **Memory 分层** | core / recall / archival | active / cold / archived + insight + working |
| **Agent 模型** | 单 agent + tools | 多 PersonAgent + turn-taking + 私聊 |
| **上下文管理** | 自编辑（edit core memory tool）| 基于检索包（retrieval_package）|
| **持久化** | Postgres 主推 | SQLite 主推（PGBackend 可选）|
| **宿主** | Letta server / API | Claude Skills / OpenAI Assistants / MCP |
| **演化** | agent 自修改 memory | 事件 → patch → snapshot → rollback |
| **可逆性** | 有限（edit 即覆盖）| 22 条不变式里 #22 强制对称撤销 |
| **世界建模** | 不关注 | 17 migrations 含人/关系/物/地/项目 |

## 何时选 Letta

- 需要一个"自我编辑 memory" 的 agent
- 已在用 Letta / MemGPT 的研究生态
- 强调"**infinite context**"隐喻

## 何时选 we-together

- 需要 **多 agent 共存 + 互动**（不只是主 agent）
- 需要**社会结构**建模（谁和谁是什么关系）
- 需要**世界**建模（物、地点、项目）
- 需要**时间模拟**（图谱 clock 可 advance）
- 重视**可回滚 + 可审计**（ADR + 不变式）

## 关键差异

Letta 的 agent 是"**自主 + 自编辑**"，但只有一个。
we-together 的 agent 是"**自主 + 可解释**（不变式 #27）"，但可以有多个，而且背后有**真正的图谱真理**（不变式 #17）。

## 可以共存吗

可以。用 plugin 适配：
- Letta agent 作为 we-together 的 `HookPlugin`，每当 we-together 写入 memory 就触发 Letta memory 同步
- 或 we-together 作为 Letta agent 的 **external memory store**

## 参考

- Letta (formerly MemGPT): https://github.com/letta-ai/letta
- 本文档为对比性，不代表 Letta 团队观点。
