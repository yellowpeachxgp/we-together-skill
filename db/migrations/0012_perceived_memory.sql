-- 0012 memories 加 perspective_person_id 列（多视角记忆）
-- 同一 event 不同 person 的 perceived_memory 可区分；NULL 表示集体视角（既有语义）

ALTER TABLE memories ADD COLUMN perspective_person_id TEXT;

CREATE INDEX IF NOT EXISTS idx_memories_perspective
    ON memories(perspective_person_id);
