# ADR 0022: Phase 24 — 图谱叙事深度

## 状态
Accepted — 2026-04-19

## 背景
图谱是 events + memories 的堆，但没有"章节/故事弧"层；同一 event 不同 person 的记忆被强制写成同一条；没有图谱级分析视角。

## 决策
### D1. Narrative arc 聚合
migration 0011 新增 `narrative_arcs` + `narrative_arc_events`。`services/narrative_service.aggregate_narrative_arcs` 让 LLM 把近 N events 聚合成 `{title, theme, summary, event_ids}` 若干章节，持久化。`list_arcs` / `playback` 支持 narrate 播放。

### D2. Perceived memory（多视角）
migration 0012 memories 加 `perspective_person_id` 列。NULL 表示集体视角，向后兼容。`services/perceived_memory_service.write_perceived_memory` 写入；`query_memories_by_perspective(include_collective=True)` 查询时可选是否合并集体记忆。

### D3. Graph analytics
`services/graph_analytics`:
- `compute_degree_centrality`：按 event_participants + event_targets→relation 计算每人的度
- `compute_group_density`：按 group_members 两两配对计算密度
- `identify_isolated_persons`：窗口内无 event 参与的 active person
- `full_report`：三项聚合

### D4. Associative recall stub
`services/associative_recall.associate_memories(seed_text)`：LLM 从候选池按主题相似度挑 top-k。不改图谱，返回候选 id 列表。留 Phase 25+ 接 narrative / persona 深化。

### D5. CLI
- `scripts/narrate.py` (aggregate / list / playback)
- `scripts/analyze.py` (degree / density / isolated / all)

## 后果
正面：图谱首次有"章节"层；同一事件可容纳不同视角；有图谱级统计；associative recall 为未来联想触发打基础。
负面：associative_recall 是 stub（没基于 embedding）；群体密度的 O(n²) 对 1000+ 人群组会慢。

## 后续
- Phase 25+：向量 embedding 替换 LLM 联想
- group density 优化到 O(n·平均度)
