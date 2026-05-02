-- 0011 narrative_arcs：把若干 events 聚合成"章节"
-- 由 services/narrative_service 的 LLM 聚合写入

CREATE TABLE IF NOT EXISTS narrative_arcs (
    arc_id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    theme TEXT,
    start_at TEXT,
    end_at TEXT,
    scene_id TEXT,
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS narrative_arc_events (
    arc_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    ordering INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (arc_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_narrative_arcs_scene
    ON narrative_arcs(scene_id);
CREATE INDEX IF NOT EXISTS idx_narrative_arc_events_arc
    ON narrative_arc_events(arc_id);
