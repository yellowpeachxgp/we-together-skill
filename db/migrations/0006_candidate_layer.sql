CREATE TABLE identity_candidates(
  candidate_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  import_job_id TEXT,
  platform TEXT,
  external_id TEXT,
  display_name TEXT,
  aliases_json TEXT,
  contact_json TEXT,
  org_json TEXT,
  match_hints_json TEXT,
  confidence REAL NOT NULL,
  confidence_tier TEXT,
  linked_person_id TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL
);

CREATE TABLE event_candidates(
  candidate_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  import_job_id TEXT,
  event_type TEXT,
  actor_candidate_ids_json TEXT,
  target_candidate_ids_json TEXT,
  group_candidate_ids_json TEXT,
  scene_hint TEXT,
  time_hint TEXT,
  summary TEXT,
  confidence REAL NOT NULL,
  confidence_tier TEXT,
  linked_event_id TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL
);

CREATE TABLE facet_candidates(
  candidate_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  import_job_id TEXT,
  target_identity_candidate_ids_json TEXT,
  target_person_id TEXT,
  facet_type TEXT NOT NULL,
  facet_key TEXT,
  facet_value TEXT,
  confidence REAL NOT NULL,
  confidence_tier TEXT,
  reason TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL
);

CREATE TABLE relation_clues(
  clue_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  import_job_id TEXT,
  participant_candidate_ids_json TEXT,
  core_type_hint TEXT,
  custom_label_hint TEXT,
  directionality_hint TEXT,
  strength_hint REAL,
  stability_hint REAL,
  summary TEXT,
  confidence REAL NOT NULL,
  confidence_tier TEXT,
  linked_relation_id TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL
);

CREATE TABLE group_clues(
  clue_id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  import_job_id TEXT,
  group_type_hint TEXT,
  group_name_hint TEXT,
  member_candidate_ids_json TEXT,
  role_hints_json TEXT,
  norm_hints_json TEXT,
  confidence REAL NOT NULL,
  confidence_tier TEXT,
  linked_group_id TEXT,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL
);

CREATE INDEX idx_identity_candidates_evidence ON identity_candidates(evidence_id);
CREATE INDEX idx_identity_candidates_status ON identity_candidates(status, confidence_tier);
CREATE INDEX idx_event_candidates_evidence ON event_candidates(evidence_id);
CREATE INDEX idx_event_candidates_status ON event_candidates(status, confidence_tier);
CREATE INDEX idx_facet_candidates_evidence ON facet_candidates(evidence_id);
CREATE INDEX idx_facet_candidates_target ON facet_candidates(target_person_id, facet_type);
CREATE INDEX idx_relation_clues_evidence ON relation_clues(evidence_id);
CREATE INDEX idx_group_clues_evidence ON group_clues(evidence_id);
