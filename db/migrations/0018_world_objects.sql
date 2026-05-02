-- 0018_world_objects.sql
-- Phase 51 / ADR 0053: 物（objects / possessions）

CREATE TABLE IF NOT EXISTS objects (
    object_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,                   -- possession / tool / artifact / gift / ...
    name TEXT,
    description TEXT,
    owner_type TEXT,                      -- person / group / scene / NULL
    owner_id TEXT,
    location_place_id TEXT,               -- places.place_id
    status TEXT NOT NULL DEFAULT 'active', -- active / inactive / lost / destroyed
    effective_from TEXT,                  -- ISO 8601（生效期）
    effective_until TEXT,                 -- ISO 8601（失效期；NULL = 仍有效）
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_objects_owner ON objects(owner_type, owner_id);
CREATE INDEX IF NOT EXISTS idx_objects_location ON objects(location_place_id);
CREATE INDEX IF NOT EXISTS idx_objects_status ON objects(status);

-- 所有权变更历史（不变式 #22 对称撤销）
CREATE TABLE IF NOT EXISTS object_ownership_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    object_id TEXT NOT NULL REFERENCES objects(object_id),
    from_owner_type TEXT,
    from_owner_id TEXT,
    to_owner_type TEXT,
    to_owner_id TEXT,
    event_id TEXT,                        -- 可关联产生此变化的 event
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_object_ownership_object
  ON object_ownership_history(object_id, recorded_at DESC);
