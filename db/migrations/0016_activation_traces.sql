-- 0016_activation_traces.sql
-- Phase 40 / ADR 0042: 神经网格式激活痕迹

CREATE TABLE IF NOT EXISTS activation_traces (
    trace_id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_entity_type TEXT NOT NULL,       -- person / relation / scene / event
    from_entity_id TEXT NOT NULL,
    to_entity_type TEXT NOT NULL,
    to_entity_id TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    trace_type TEXT NOT NULL,             -- relation_traversal / scene_participation /
                                          -- event_mention / retrieval_hit / multi_hop
    hop_distance INTEGER NOT NULL DEFAULT 1,
    scene_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    activated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_act_trace_from
  ON activation_traces(from_entity_type, from_entity_id, activated_at DESC);
CREATE INDEX IF NOT EXISTS idx_act_trace_to
  ON activation_traces(to_entity_type, to_entity_id, activated_at DESC);
CREATE INDEX IF NOT EXISTS idx_act_trace_scene
  ON activation_traces(scene_id, activated_at DESC);

-- 按"起点 + 终点"聚合后的频率视图（frequent pair）可以动态查，这里不建物化视图
