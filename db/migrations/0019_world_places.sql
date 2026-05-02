-- 0019_world_places.sql
-- Phase 51 / ADR 0053: 地点（places）

CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    scope TEXT,                            -- physical / virtual / venue / room / city / ...
    parent_place_id TEXT REFERENCES places(place_id),
    visibility TEXT NOT NULL DEFAULT 'shared',
    status TEXT NOT NULL DEFAULT 'active',
    effective_from TEXT,
    effective_until TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_places_parent ON places(parent_place_id);
CREATE INDEX IF NOT EXISTS idx_places_status ON places(status);
CREATE INDEX IF NOT EXISTS idx_places_name ON places(name);
