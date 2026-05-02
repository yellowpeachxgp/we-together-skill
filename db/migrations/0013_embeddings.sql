-- 0013 embeddings：为 memory/event/person 持久化向量
-- BLOB 存 struct packed float32；model_name 记录 provider 以便切换识别

CREATE TABLE IF NOT EXISTS memory_embeddings (
    memory_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vec BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_embeddings (
    event_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vec BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS person_embeddings (
    person_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vec BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memory_embeddings_model ON memory_embeddings(model_name);
CREATE INDEX IF NOT EXISTS idx_event_embeddings_model ON event_embeddings(model_name);
CREATE INDEX IF NOT EXISTS idx_person_embeddings_model ON person_embeddings(model_name);
