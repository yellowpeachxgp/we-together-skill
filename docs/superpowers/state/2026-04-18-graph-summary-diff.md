# Phase 8-12 Graph Summary Report（v0.8.0 基线）

时间：2026-04-18

## Pre-Phase-8 基线（Phase 7 收尾）

- 测试基线：216 passed
- migrations: 0001-0006
- schema：核心实体 + 候选中间层 + 运行时缓存

## Post-Phase-12 基线（本轮收尾）

- 测试基线：**281 passed**（+65）
- migrations: 0001-**0008**（新增 cold_memories / external_person_refs）
- Demo seed（Society C）graph_summary 示例：

```json
{
  "person_count": 8,
  "relation_count": 8,
  "scene_count": 3,
  "event_count": 5,
  "memory_count": 3,
  "patch_count": 3,
  "candidate_layer_counts": {
    "identity_candidates": {},
    "event_candidates": {},
    "facet_candidates": {},
    "relation_clues": {},
    "group_clues": {}
  },
  "people": ["Alice", "Bob", "Carol", "Dan", "Eve", "Frank", "Grace", "Henry"]
}
```

## 关键能力差集（Phase 7 → Phase 12）

| 维度 | Phase 7 末尾 | Phase 12 末尾 |
|---|---|---|
| migrations | 0006 | 0008 |
| tests | 216 | 281 |
| importers | narration / text_chat / email / auto / file / directory / wechat_text / llm_extraction | + imessage / wechat_db / mbox / image / social |
| adapters | claude / openai_compat | + feishu / langchain / coze / mcp |
| runtime 能力 | 单 scene retrieval | + multi_scene / cross_scene_echoes / debug breakdown |
| 演化服务 | relation_drift / state_decay / auto_resolve / scene_transition / self_activation | + persona_drift / memory_cluster / memory_condenser / pair_interactions / relation_conflict |
| 归档 | 无 | cold_memories + restore |
| 联邦 | 无 | external_person_refs + event_bus + branch_console + tenant_router |
| 观测 | graph_summary / bench | + observability logger+metrics / bench_large / metrics_server |
| 配置 | env var 散在 | toml + WeTogetherConfig + env 覆盖 |
| 错误 | 多处 ValueError | WeTogetherError 层级 |
| schema 安全 | 无检测 | schema_version 漂移检测 |

## 新增 CLI 脚本

`condense_memories.py` / `cold_memory.py` / `agent_chat.py` / `package_skill.py` /
`branch_console.py` / `bench_large.py` / `metrics_server.py`

## 结论

Phase 8-12 让 `we together` 从"功能齐全 demo"推进到"可被真实 skill 宿主接纳、可长期运行、可联邦协同"的 v0.8.0 状态。下一阶段（Phase 13+）的方向由 ADR 0009 固化的 5 条不变式约束，并在 `mega-plan.md` 的"不在本轮范围"段落中列出。
