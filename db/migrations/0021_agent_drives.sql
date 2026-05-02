-- 0021_agent_drives.sql
-- Phase 52 / ADR 0054: Agent 内在驱动力 / 需求 / 意图

CREATE TABLE IF NOT EXISTS agent_drives (
    drive_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    drive_type TEXT NOT NULL,             -- connection / curiosity / resolve / obligation / rest / ...
    intensity REAL NOT NULL DEFAULT 0.5,   -- 0.0 - 1.0
    source_memory_ids_json TEXT NOT NULL DEFAULT '[]',  -- 引发该 drive 的 memory
    source_event_ids_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active', -- active / satisfied / expired
    satisfied_by_event_id TEXT,            -- 如果被满足，关联 event
    activated_at TEXT NOT NULL DEFAULT (datetime('now')),
    satisfied_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_drives_person ON agent_drives(person_id, status);
CREATE INDEX IF NOT EXISTS idx_drives_type ON agent_drives(drive_type, status);

-- Autonomous action log（追溯自主行为，不变式 #27）
CREATE TABLE IF NOT EXISTS autonomous_actions (
    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL,
    action_type TEXT NOT NULL,            -- speak / reach_out / reflect / avoid / ...
    triggered_by_drive_id TEXT,
    triggered_by_memory_id TEXT,
    triggered_by_trace_id INTEGER,
    output_event_id TEXT,
    rationale TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_auto_actions_person
  ON autonomous_actions(person_id, created_at DESC);
