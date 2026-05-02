-- 0008 external_person_refs：联邦引用外部 skill 的 person
-- 不复制远端数据，只记录引用元数据，供 retrieval 按 policy 拉取

CREATE TABLE IF NOT EXISTS external_person_refs (
    ref_id TEXT PRIMARY KEY,
    external_skill_name TEXT NOT NULL,
    external_person_id TEXT NOT NULL,
    local_alias TEXT,
    display_name TEXT,
    trust_level REAL DEFAULT 0.5,
    policy TEXT DEFAULT 'lazy',  -- lazy|eager|never
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(external_skill_name, external_person_id)
);

CREATE INDEX IF NOT EXISTS idx_external_refs_skill
    ON external_person_refs(external_skill_name);
