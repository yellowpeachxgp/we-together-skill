CREATE TABLE person_facets(
  facet_id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL,
  facet_type TEXT NOT NULL,
  facet_key TEXT NOT NULL,
  facet_value_json TEXT NOT NULL,
  confidence REAL,
  source_event_refs_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE relation_facets(
  facet_id TEXT PRIMARY KEY,
  relation_id TEXT NOT NULL,
  facet_key TEXT NOT NULL,
  facet_value_json TEXT NOT NULL,
  confidence REAL,
  source_event_refs_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE group_members(
  group_id TEXT NOT NULL,
  person_id TEXT NOT NULL,
  role_label TEXT,
  joined_at TEXT,
  left_at TEXT,
  status TEXT NOT NULL,
  metadata_json TEXT,
  PRIMARY KEY(group_id, person_id, status)
);

CREATE TABLE scene_participants(
  scene_id TEXT NOT NULL,
  person_id TEXT NOT NULL,
  activation_score REAL,
  activation_state TEXT NOT NULL,
  is_speaking INTEGER NOT NULL DEFAULT 0,
  reason_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE scene_active_relations(
  scene_id TEXT NOT NULL,
  relation_id TEXT NOT NULL,
  activation_score REAL,
  reason_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE memory_owners(
  memory_id TEXT NOT NULL,
  owner_type TEXT NOT NULL,
  owner_id TEXT NOT NULL,
  role_label TEXT
);

CREATE TABLE event_participants(
  event_id TEXT NOT NULL,
  person_id TEXT NOT NULL,
  participant_role TEXT
);

CREATE TABLE event_targets(
  event_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  impact_hint TEXT
);
