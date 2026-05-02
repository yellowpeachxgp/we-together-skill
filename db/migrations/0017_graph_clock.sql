-- 0017_graph_clock.sql
-- Phase 45 / ADR 0047: 图谱内部时钟

CREATE TABLE IF NOT EXISTS graph_clock (
    id INTEGER PRIMARY KEY CHECK (id = 1),   -- 单行
    simulated_now TEXT,                       -- ISO 8601；NULL 表示使用 real time
    speed_factor REAL NOT NULL DEFAULT 1.0,
    frozen INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO graph_clock(id, simulated_now, speed_factor, frozen, updated_at)
VALUES (1, NULL, 1.0, 0, datetime('now'));

CREATE TABLE IF NOT EXISTS graph_clock_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,      -- set / advance / freeze / unfreeze
    before_value TEXT,
    after_value TEXT,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);
