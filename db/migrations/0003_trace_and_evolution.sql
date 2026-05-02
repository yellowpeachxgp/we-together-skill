CREATE TABLE import_jobs(
  import_job_id TEXT PRIMARY KEY,
  source_type TEXT NOT NULL,
  source_platform TEXT,
  operator TEXT,
  status TEXT NOT NULL,
  stats_json TEXT,
  error_log TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE raw_evidences(
  evidence_id TEXT PRIMARY KEY,
  import_job_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_platform TEXT,
  source_locator TEXT,
  content_type TEXT NOT NULL,
  normalized_text TEXT,
  timestamp TEXT,
  file_path TEXT,
  content_hash TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE patches(
  patch_id TEXT PRIMARY KEY,
  source_event_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT,
  operation TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  confidence REAL,
  reason TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  applied_at TEXT
);

CREATE TABLE snapshots(
  snapshot_id TEXT PRIMARY KEY,
  based_on_snapshot_id TEXT,
  trigger_event_id TEXT,
  summary TEXT,
  graph_hash TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE snapshot_entities(
  snapshot_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  entity_hash TEXT
);

CREATE TABLE local_branches(
  branch_id TEXT PRIMARY KEY,
  scope_type TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  status TEXT NOT NULL,
  reason TEXT,
  created_from_event_id TEXT,
  created_at TEXT NOT NULL,
  resolved_at TEXT
);

CREATE TABLE branch_candidates(
  candidate_id TEXT PRIMARY KEY,
  branch_id TEXT NOT NULL,
  label TEXT,
  payload_json TEXT NOT NULL,
  confidence REAL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);
