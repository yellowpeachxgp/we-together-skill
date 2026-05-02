# ADR 0027: Phase 25-27 综合 + 不变式扩展至 16 条

## 状态
Accepted — 2026-04-19

## 背景
Phase 25-27 让 we-together-skill 从 v0.11.0 迈向 v0.12.0：真 LLM 集成 / 向量化图谱 / 真生产化三条主干落地。本 ADR 聚合共同抽象与新不变式。

## 决策

### D1. "双路径"设计哲学
所有真 SDK 相关能力（LLM tool_use / streaming / embedding）都采用"**真 provider 优先 + Mock fallback**"双路径：
- 真 provider（Anthropic/OpenAI/sentence-transformers）在 CI 中 `# pragma: no cover` 标记
- Mock 负责所有测试路径
- `_prefers_native` 这类检测函数让 runtime 自动切换

### D2. 新增不变式（在 ADR 0023 14 条基础上追加）

15. **LLM 能力的单元测试必须走 Mock，真 SDK 只在集成/手动验证时启用**。core path 不得在 import 阶段 require 真 SDK（延迟 import）。

16. **向量能力必须有 BLOB 编解码契约，不可依赖 numpy**。核心路径（encode/decode/cosine/top_k）纯 Python；真规模场景由外部库覆盖（FAISS/chromadb），不污染核心。

### D3. 双版本扩展（optional extras）
`pip install we-together-skill[anthropic]` / `[openai]` / `[embedding]` / `[vision]` / `[audio]` / `[nats]` / `[redis]` / `[dev]`。每个 extra 对应一个延迟 import 的 provider。

## 版本锚点
- tag: `v0.12.0`
- 测试基线: **410 passed**
- schema 版本: 0013（migrations 0001-0013）
- ADR 总数: 27
- Coverage: 90%
- benchmarks: 7（新增 embedding_retrieval）

## 下一阶段候选（Phase 28+）
- SQLite 向量插件 / FAISS 索引
- 真 streaming SSE 反压 + 断线重连
- PyPI 正式发布（需 token）
- 1M 规模压测
- NATS drain 真实现
- branch_console fastapi 升级 + RBAC 集成
- i18n prompt
