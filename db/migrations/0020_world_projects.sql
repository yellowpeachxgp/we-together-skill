-- 0020_world_projects.sql
-- Phase 51 / ADR 0053: 项目 / 任务（projects）

CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    goal TEXT,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',  -- active / completed / abandoned / archived
    priority TEXT,                           -- low / medium / high
    started_at TEXT,
    due_at TEXT,
    ended_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_due ON projects(due_at);
