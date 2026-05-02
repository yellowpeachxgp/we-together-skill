-- 0009 persona_history：每次 persona drift 记录一个历史行
-- 允许 as_of 查询某时刻的 persona_summary / style_summary

CREATE TABLE IF NOT EXISTS persona_history (
    history_id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    persona_summary TEXT,
    style_summary TEXT,
    boundary_summary TEXT,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    source_reason TEXT,
    confidence REAL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_persona_history_person_valid
    ON persona_history(person_id, valid_from);
