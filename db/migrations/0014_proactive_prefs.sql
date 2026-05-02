-- 0014 proactive_prefs：per-person 主动图谱偏好
-- mute=True 表示该 person 不会被主动 trigger

CREATE TABLE IF NOT EXISTS proactive_prefs (
    person_id TEXT PRIMARY KEY,
    mute INTEGER NOT NULL DEFAULT 0,
    trigger_consents TEXT NOT NULL DEFAULT '{}',  -- JSON {trigger_name: bool}
    updated_at TEXT NOT NULL
);
