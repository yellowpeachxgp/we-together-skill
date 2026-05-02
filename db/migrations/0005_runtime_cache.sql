CREATE TABLE entity_tags(
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  weight REAL
);

CREATE TABLE entity_aliases(
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  alias TEXT NOT NULL,
  alias_type TEXT
);

CREATE TABLE entity_links(
  from_type TEXT NOT NULL,
  from_id TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  to_type TEXT NOT NULL,
  to_id TEXT NOT NULL,
  weight REAL,
  metadata_json TEXT
);

CREATE TABLE retrieval_cache(
  cache_id TEXT PRIMARY KEY,
  scene_id TEXT,
  cache_type TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  expires_at TEXT,
  created_at TEXT NOT NULL
);
