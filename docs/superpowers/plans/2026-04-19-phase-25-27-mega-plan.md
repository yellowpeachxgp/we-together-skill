# Phase 25-27 Mega Plan 归档（2026-04-19 第五轮无人值守）

## 目标
v0.11.0 (392 passed, 23 ADR) → v0.12.0：真 LLM / 向量化 / 真生产化。

## 达成情况

| Phase | 主题 | 切片 | 测试增量 |
|---|---|---|---|
| 25 | 真 LLM 集成 | TL-1~6 | +7 |
| 26 | 向量化图谱 | VE-1~8 | +11 |
| 27 | 规模与真生产 | PD-1/2/3/4/8/9 | 无新测试（基建） |

**总增量**：392 → 410 passed（+18），commits ≈ 6，Coverage 首版 90%。

## 新增模块

- `llm/providers/embedding.py`（Mock + OpenAI + sentence-transformers）
- `services/vector_similarity.py` / `services/embedding_recall.py`
- `eval/embedding_retrieval_eval.py`
- `observability/llm_hooks.py`
- `runtime/agent_runner.py` 升级 native 路径
- `services/chat_service.run_turn_stream`
- `db/migrations/0013_embeddings.sql`
- `scripts/embed_backfill.py`
- `.github/workflows/publish.yml`
- `.coveragerc`
- `docs/release_notes_template.md`
- `benchmarks/embedding_retrieval_groundtruth.json`

## 不在本轮范围

- 真发 pypi.org（需账号 token，checklist 已备）
- 1M 规模真跑
- NATS drain 真实现
- SQLite 向量插件
- memory_cluster / retrieval 默认切换到 embedding（保留 Jaccard fallback，需 benchmark 后决策）
- 真 streaming SSE 反压

## 下一轮候选

参考 ADR 0027 末尾"Phase 28+"。
