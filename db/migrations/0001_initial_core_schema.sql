CREATE TABLE persons(
  person_id TEXT PRIMARY KEY,
  primary_name TEXT NOT NULL,
  status TEXT NOT NULL,
  summary TEXT,
  persona_summary TEXT,
  work_summary TEXT,
  life_summary TEXT,
  style_summary TEXT,
  boundary_summary TEXT,
  confidence REAL,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE identity_links(
  identity_id TEXT PRIMARY KEY,
  person_id TEXT,
  platform TEXT NOT NULL,
  external_id TEXT,
  display_name TEXT,
  contact_json TEXT,
  org_json TEXT,
  match_method TEXT,
  confidence REAL NOT NULL,
  is_user_confirmed INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  conflict_flags_json TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE relations(
  relation_id TEXT PRIMARY KEY,
  core_type TEXT NOT NULL,
  custom_label TEXT,
  summary TEXT,
  directionality TEXT,
  strength REAL,
  stability REAL,
  visibility TEXT,
  status TEXT NOT NULL,
  time_start TEXT,
  time_end TEXT,
  confidence REAL,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE groups(
  group_id TEXT PRIMARY KEY,
  group_type TEXT NOT NULL,
  name TEXT,
  summary TEXT,
  norms_summary TEXT,
  status TEXT NOT NULL,
  confidence REAL,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE scenes(
  scene_id TEXT PRIMARY KEY,
  scene_type TEXT NOT NULL,
  group_id TEXT,
  trigger_event_id TEXT,
  scene_summary TEXT,
  location_scope TEXT,
  channel_scope TEXT,
  visibility_scope TEXT,
  time_scope TEXT,
  role_scope TEXT,
  access_scope TEXT,
  privacy_scope TEXT,
  activation_barrier TEXT,
  environment_json TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE events(
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  source_type TEXT NOT NULL,
  scene_id TEXT,
  group_id TEXT,
  timestamp TEXT NOT NULL,
  summary TEXT,
  visibility_level TEXT NOT NULL,
  confidence REAL,
  is_structured INTEGER NOT NULL DEFAULT 0,
  raw_evidence_refs_json TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE memories(
  memory_id TEXT PRIMARY KEY,
  memory_type TEXT NOT NULL,
  summary TEXT NOT NULL,
  emotional_tone TEXT,
  relevance_score REAL,
  confidence REAL,
  is_shared INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE states(
  state_id TEXT PRIMARY KEY,
  scope_type TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  state_type TEXT NOT NULL,
  value_json TEXT NOT NULL,
  confidence REAL,
  is_inferred INTEGER NOT NULL DEFAULT 1,
  decay_policy TEXT,
  source_event_refs_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
