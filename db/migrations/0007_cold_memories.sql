-- 0007 cold_memories：长期未激活的记忆冷存储表
-- 迁移时将 memories 行移入 cold_memories，保留原字段 + archived_at 审计信息
-- retrieval 默认不加载 cold_memories；调用方显式 include_cold=True 才读取

CREATE TABLE IF NOT EXISTS cold_memories (
    memory_id TEXT PRIMARY KEY,
    memory_type TEXT NOT NULL,
    summary TEXT,
    emotional_tone TEXT,
    relevance_score REAL,
    confidence REAL,
    is_shared INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    original_created_at TEXT,
    original_updated_at TEXT,
    archived_at TEXT NOT NULL,
    archive_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_cold_memories_archived_at
    ON cold_memories(archived_at DESC);

-- cold_memory_owners：归档时保留原 owners
CREATE TABLE IF NOT EXISTS cold_memory_owners (
    memory_id TEXT NOT NULL,
    owner_type TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    role_label TEXT,
    PRIMARY KEY (memory_id, owner_type, owner_id)
);
