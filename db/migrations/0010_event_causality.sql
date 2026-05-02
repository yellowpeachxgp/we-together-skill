-- 0010 event_causality：event A → event B 的有向因果边
-- 支持 LLM 推理的因果链表达

CREATE TABLE IF NOT EXISTS event_causality (
    edge_id TEXT PRIMARY KEY,
    cause_event_id TEXT NOT NULL,
    effect_event_id TEXT NOT NULL,
    confidence REAL,
    reason TEXT,
    source TEXT,  -- 'llm' | 'rule' | 'manual'
    created_at TEXT NOT NULL,
    UNIQUE(cause_event_id, effect_event_id)
);

CREATE INDEX IF NOT EXISTS idx_causality_cause ON event_causality(cause_event_id);
CREATE INDEX IF NOT EXISTS idx_causality_effect ON event_causality(effect_event_id);
