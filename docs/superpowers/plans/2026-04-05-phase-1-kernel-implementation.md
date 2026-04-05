# Phase 1 Kernel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 `we together` 第一阶段可运行的社会图谱内核，实现 SQLite 主库、事件到 patch 的演化链、基础 importer 契约和最小运行时检索包。

**Architecture:** 采用 Skill-first 架构，使用 SQLite 存储规范主对象与留痕对象，文件系统存储原始材料与派生文本。实现顺序以图谱内核优先，先落 schema、迁移、patch/snapshot、identity 融合基础，再接最小 importer 和运行时检索包。

**Tech Stack:** Python 3.11+, SQLite, pytest, pydantic（可选）, typer 或 argparse, pathlib, json

---

## 文件结构

### 需要创建的核心目录

- `src/we_together/`
- `src/we_together/db/`
- `src/we_together/domain/`
- `src/we_together/importers/`
- `src/we_together/runtime/`
- `src/we_together/services/`
- `scripts/`
- `tests/`
- `tests/db/`
- `tests/importers/`
- `tests/runtime/`
- `db/migrations/`
- `db/seeds/`
- `data/raw/`
- `data/derived/`
- `data/snapshots/`
- `data/runtime/`

### 需要创建的核心文件

- `pyproject.toml`
- `src/we_together/__init__.py`
- `src/we_together/config.py`
- `src/we_together/db/connection.py`
- `src/we_together/db/migrator.py`
- `src/we_together/db/bootstrap.py`
- `src/we_together/db/schema.py`
- `src/we_together/domain/models.py`
- `src/we_together/domain/enums.py`
- `src/we_together/services/event_service.py`
- `src/we_together/services/patch_service.py`
- `src/we_together/services/snapshot_service.py`
- `src/we_together/services/identity_fusion_service.py`
- `src/we_together/importers/base.py`
- `src/we_together/importers/text_narration_importer.py`
- `src/we_together/runtime/retrieval_package.py`
- `src/we_together/runtime/activation.py`
- `scripts/bootstrap.py`
- `tests/conftest.py`
- `tests/db/test_bootstrap.py`
- `tests/db/test_migrations.py`
- `tests/db/test_schema_constraints.py`
- `tests/services/test_event_patch_flow.py`
- `tests/services/test_identity_fusion.py`
- `tests/importers/test_text_narration_importer.py`
- `tests/runtime/test_retrieval_package.py`

---

### Task 1: 初始化 Python 工程骨架

**Files:**
- Create: `pyproject.toml`
- Create: `src/we_together/__init__.py`
- Create: `src/we_together/config.py`
- Test: `tests/conftest.py`

- [ ] **Step 1: 写最小工程配置测试前置**

```python
# tests/conftest.py
from pathlib import Path
import tempfile
import pytest


@pytest.fixture
def temp_project_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)
```

- [ ] **Step 2: 创建工程配置**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "we-together"
version = "0.1.0"
description = "Skill-first social graph runtime"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

```python
# src/we_together/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"
```

```python
# src/we_together/config.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    db_dir: Path
    data_dir: Path


def build_app_paths(root: Path) -> AppPaths:
    return AppPaths(
        root=root,
        db_dir=root / "db",
        data_dir=root / "data",
    )
```

- [ ] **Step 3: 运行最小测试**

Run: `pytest -q`
Expected: PASS with `1 passed`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml src/we_together/__init__.py src/we_together/config.py tests/conftest.py
git commit -m "chore: initialize python project skeleton"
```

### Task 2: 实现目录 bootstrap

**Files:**
- Create: `src/we_together/db/bootstrap.py`
- Create: `scripts/bootstrap.py`
- Test: `tests/db/test_bootstrap.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/db/test_bootstrap.py
from we_together.db.bootstrap import bootstrap_directories


def test_bootstrap_directories_creates_runtime_layout(temp_project_dir):
    bootstrap_directories(temp_project_dir)

    assert (temp_project_dir / "db").exists()
    assert (temp_project_dir / "db" / "migrations").exists()
    assert (temp_project_dir / "db" / "seeds").exists()
    assert (temp_project_dir / "data" / "raw").exists()
    assert (temp_project_dir / "data" / "derived").exists()
    assert (temp_project_dir / "data" / "snapshots").exists()
    assert (temp_project_dir / "data" / "runtime").exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/db/test_bootstrap.py -q`
Expected: FAIL with `ModuleNotFoundError` or missing function

- [ ] **Step 3: 写最小实现**

```python
# src/we_together/db/bootstrap.py
from pathlib import Path


RUNTIME_DIRS = [
    "db",
    "db/migrations",
    "db/seeds",
    "data/raw",
    "data/derived",
    "data/snapshots",
    "data/runtime",
]


def bootstrap_directories(root: Path) -> None:
    for rel in RUNTIME_DIRS:
        (root / rel).mkdir(parents=True, exist_ok=True)
```

```python
# scripts/bootstrap.py
from pathlib import Path
from we_together.db.bootstrap import bootstrap_directories


if __name__ == "__main__":
    bootstrap_directories(Path.cwd())
    print("bootstrap directories ready")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/db/test_bootstrap.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/we_together/db/bootstrap.py scripts/bootstrap.py tests/db/test_bootstrap.py
git commit -m "feat: add bootstrap directory creation"
```

### Task 3: 建立迁移执行器

**Files:**
- Create: `src/we_together/db/connection.py`
- Create: `src/we_together/db/migrator.py`
- Test: `tests/db/test_migrations.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/db/test_migrations.py
from pathlib import Path
import sqlite3

from we_together.db.migrator import run_migrations


def test_run_migrations_creates_schema_migrations_table(temp_project_dir):
    db_path = temp_project_dir / "db" / "main.sqlite3"
    migrations_dir = temp_project_dir / "db" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)
    (migrations_dir / "0001_init.sql").write_text(
        "CREATE TABLE sample(id TEXT PRIMARY KEY);",
        encoding="utf-8",
    )

    run_migrations(db_path, migrations_dir)

    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()

    assert "schema_migrations" in tables
    assert "sample" in tables
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/db/test_migrations.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# src/we_together/db/connection.py
import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn
```

```python
# src/we_together/db/migrator.py
from pathlib import Path

from we_together.db.connection import connect


def run_migrations(db_path: Path, migrations_dir: Path) -> None:
    conn = connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations(
            version TEXT PRIMARY KEY,
            description TEXT,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    applied = {
        row[0]
        for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
    }
    for path in sorted(migrations_dir.glob("*.sql")):
        version = path.stem.split("_", 1)[0]
        if version in applied:
            continue
        conn.executescript(path.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations(version, description) VALUES(?, ?)",
            (version, path.name),
        )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/db/test_migrations.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/we_together/db/connection.py src/we_together/db/migrator.py tests/db/test_migrations.py
git commit -m "feat: add sqlite migration runner"
```

### Task 4: 写首版 schema 迁移文件

**Files:**
- Create: `db/migrations/0001_initial_core_schema.sql`
- Create: `db/migrations/0002_connection_tables.sql`
- Create: `db/migrations/0003_trace_and_evolution.sql`
- Create: `db/migrations/0004_indexes_and_constraints.sql`
- Test: `tests/db/test_schema_constraints.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/db/test_schema_constraints.py
import sqlite3

from we_together.db.migrator import run_migrations


def test_core_tables_exist_after_migration(temp_project_dir):
    db_path = temp_project_dir / "db" / "main.sqlite3"
    migrations_dir = temp_project_dir / "db" / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    for src in ("db/migrations/0001_initial_core_schema.sql",
                "db/migrations/0002_connection_tables.sql",
                "db/migrations/0003_trace_and_evolution.sql",
                "db/migrations/0004_indexes_and_constraints.sql"):
        target = migrations_dir / src.split("/")[-1]
        target.write_text(open(src, "r", encoding="utf-8").read(), encoding="utf-8")

    run_migrations(db_path, migrations_dir)

    conn = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    conn.close()

    assert "persons" in tables
    assert "identity_links" in tables
    assert "events" in tables
    assert "patches" in tables
    assert "snapshots" in tables
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/db/test_schema_constraints.py -q`
Expected: FAIL

- [ ] **Step 3: 写迁移文件**

```sql
-- db/migrations/0001_initial_core_schema.sql
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
```

```sql
-- db/migrations/0002_connection_tables.sql
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
```

```sql
-- db/migrations/0003_trace_and_evolution.sql
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
```

```sql
-- db/migrations/0004_indexes_and_constraints.sql
CREATE UNIQUE INDEX idx_identity_unique ON identity_links(platform, external_id);
CREATE INDEX idx_identity_person_id ON identity_links(person_id);
CREATE INDEX idx_relations_core_status ON relations(core_type, status);
CREATE INDEX idx_group_members_group_status ON group_members(group_id, status);
CREATE INDEX idx_scene_participants_scene_state ON scene_participants(scene_id, activation_state);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_events_type_timestamp ON events(event_type, timestamp);
CREATE INDEX idx_memories_shared_status ON memories(is_shared, status);
CREATE UNIQUE INDEX idx_states_scope_type ON states(scope_type, scope_id, state_type);
CREATE INDEX idx_raw_evidences_job ON raw_evidences(import_job_id);
CREATE INDEX idx_patches_source_status ON patches(source_event_id, status);
CREATE INDEX idx_local_branches_scope_status ON local_branches(scope_type, scope_id, status);
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/db/test_schema_constraints.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add db/migrations tests/db/test_schema_constraints.py
git commit -m "feat: add phase 1 sqlite schema migrations"
```

### Task 5: 增加枚举与领域模型

**Files:**
- Create: `src/we_together/domain/enums.py`
- Create: `src/we_together/domain/models.py`
- Test: `tests/runtime/test_retrieval_package.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/runtime/test_retrieval_package.py
from we_together.domain.enums import ActivationState, ResponseMode


def test_activation_and_response_enums_have_expected_values():
    assert ActivationState.LATENT.value == "latent"
    assert ResponseMode.SINGLE_PRIMARY.value == "single_primary"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/runtime/test_retrieval_package.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# src/we_together/domain/enums.py
from enum import Enum


class ActivationState(str, Enum):
    INACTIVE = "inactive"
    LATENT = "latent"
    EXPLICIT = "explicit"


class ResponseMode(str, Enum):
    SINGLE_PRIMARY = "single_primary"
    PRIMARY_PLUS_SUPPORT = "primary_plus_support"
    MULTI_PARALLEL = "multi_parallel"
```

```python
# src/we_together/domain/models.py
from dataclasses import dataclass, field


@dataclass
class RuntimeParticipant:
    person_id: str
    display_name: str
    scene_role: str
    activation_state: str
    activation_score: float = 0.0
    is_speaking: bool = False
    reasons: list[str] = field(default_factory=list)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/runtime/test_retrieval_package.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/we_together/domain/enums.py src/we_together/domain/models.py tests/runtime/test_retrieval_package.py
git commit -m "feat: add domain enums and runtime participant model"
```

### Task 6: 实现 Event -> Patch 基础链路

**Files:**
- Create: `src/we_together/services/event_service.py`
- Create: `src/we_together/services/patch_service.py`
- Test: `tests/services/test_event_patch_flow.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/services/test_event_patch_flow.py
from we_together.services.patch_service import build_patch


def test_build_patch_creates_structured_patch_payload():
    patch = build_patch(
        source_event_id="evt_1",
        target_type="state",
        target_id="state_1",
        operation="update_state",
        payload={"value": {"mood": "tense"}},
        confidence=0.9,
        reason="recent conflict event",
    )

    assert patch["source_event_id"] == "evt_1"
    assert patch["operation"] == "update_state"
    assert patch["payload_json"]["value"]["mood"] == "tense"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/services/test_event_patch_flow.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# src/we_together/services/event_service.py
from dataclasses import dataclass


@dataclass
class EventRecord:
    event_id: str
    event_type: str
    source_type: str
    timestamp: str
    summary: str
```

```python
# src/we_together/services/patch_service.py
from datetime import datetime, UTC
import uuid


def build_patch(
    source_event_id: str,
    target_type: str,
    target_id: str | None,
    operation: str,
    payload: dict,
    confidence: float,
    reason: str,
) -> dict:
    return {
        "patch_id": f"patch_{uuid.uuid4().hex}",
        "source_event_id": source_event_id,
        "target_type": target_type,
        "target_id": target_id,
        "operation": operation,
        "payload_json": payload,
        "confidence": confidence,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
        "applied_at": None,
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/services/test_event_patch_flow.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/we_together/services/event_service.py src/we_together/services/patch_service.py tests/services/test_event_patch_flow.py
git commit -m "feat: add event to patch flow primitives"
```

### Task 7: 实现 Identity 融合基础评分器

**Files:**
- Create: `src/we_together/services/identity_fusion_service.py`
- Test: `tests/services/test_identity_fusion.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/services/test_identity_fusion.py
from we_together.services.identity_fusion_service import score_candidates


def test_score_candidates_prefers_strong_match():
    score = score_candidates(
        left={"platform": "email", "external_id": "a@example.com", "display_name": "Alice"},
        right={"platform": "email", "external_id": "a@example.com", "display_name": "Alice Zhang"},
    )
    assert score >= 0.9
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/services/test_identity_fusion.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# src/we_together/services/identity_fusion_service.py
def score_candidates(left: dict, right: dict) -> float:
    if (
        left.get("platform") == right.get("platform")
        and left.get("external_id")
        and left.get("external_id") == right.get("external_id")
    ):
        return 1.0

    if left.get("display_name") and left.get("display_name") == right.get("display_name"):
        return 0.7

    return 0.1
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/services/test_identity_fusion.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/we_together/services/identity_fusion_service.py tests/services/test_identity_fusion.py
git commit -m "feat: add identity fusion scoring baseline"
```

### Task 8: 实现统一 importer 基类与 narration importer

**Files:**
- Create: `src/we_together/importers/base.py`
- Create: `src/we_together/importers/text_narration_importer.py`
- Test: `tests/importers/test_text_narration_importer.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/importers/test_text_narration_importer.py
from we_together.importers.text_narration_importer import import_narration_text


def test_import_narration_text_returns_import_result_shape():
    result = import_narration_text(
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    assert "raw_evidences" in result
    assert "identity_candidates" in result
    assert "event_candidates" in result
    assert "relation_clues" in result
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/importers/test_text_narration_importer.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# src/we_together/importers/base.py
from dataclasses import dataclass, field


@dataclass
class ImportResult:
    raw_evidences: list = field(default_factory=list)
    identity_candidates: list = field(default_factory=list)
    event_candidates: list = field(default_factory=list)
    facet_candidates: list = field(default_factory=list)
    relation_clues: list = field(default_factory=list)
    group_clues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    stats: dict = field(default_factory=dict)
```

```python
# src/we_together/importers/text_narration_importer.py
import uuid
from we_together.importers.base import ImportResult


def import_narration_text(text: str, source_name: str) -> dict:
    evidence_id = f"evi_{uuid.uuid4().hex}"
    result = ImportResult(
        raw_evidences=[{
            "evidence_id": evidence_id,
            "source_type": "narration",
            "source_platform": "manual",
            "source_locator": source_name,
            "content_type": "text",
            "raw_content": text,
            "normalized_text": text,
        }],
        identity_candidates=[],
        event_candidates=[],
        facet_candidates=[],
        relation_clues=[],
        group_clues=[],
        warnings=[],
        stats={"evidence_count": 1},
    )
    return result.__dict__
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/importers/test_text_narration_importer.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/we_together/importers/base.py src/we_together/importers/text_narration_importer.py tests/importers/test_text_narration_importer.py
git commit -m "feat: add importer base and narration importer"
```

### Task 9: 实现运行时检索包构造器

**Files:**
- Create: `src/we_together/runtime/retrieval_package.py`
- Create: `src/we_together/runtime/activation.py`
- Modify: `tests/runtime/test_retrieval_package.py`

- [ ] **Step 1: 扩展失败测试**

```python
# tests/runtime/test_retrieval_package.py
from we_together.runtime.retrieval_package import build_runtime_retrieval_package


def test_build_runtime_retrieval_package_contains_required_sections():
    package = build_runtime_retrieval_package(
        scene={"scene_id": "scene_1", "scene_type": "private_chat", "summary": "late night chat"},
        environment={"location_scope": "remote", "channel_scope": "private_dm"},
        participants=[],
        active_relations=[],
        relevant_memories=[],
        current_states=[],
        activation_map=[],
        response_policy={"mode": "single_primary"},
    )

    assert "scene_summary" in package
    assert "environment_constraints" in package
    assert "participants" in package
    assert "response_policy" in package
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/runtime/test_retrieval_package.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# src/we_together/runtime/activation.py
def mark_latent(participants: list[dict]) -> list[dict]:
    result = []
    for item in participants:
        copied = dict(item)
        copied.setdefault("activation_state", "latent")
        result.append(copied)
    return result
```

```python
# src/we_together/runtime/retrieval_package.py
def build_runtime_retrieval_package(
    scene: dict,
    environment: dict,
    participants: list,
    active_relations: list,
    relevant_memories: list,
    current_states: list,
    activation_map: list,
    response_policy: dict,
) -> dict:
    return {
        "scene_summary": scene,
        "environment_constraints": environment,
        "participants": participants,
        "active_relations": active_relations,
        "relevant_memories": relevant_memories,
        "current_states": current_states,
        "activation_map": activation_map,
        "response_policy": response_policy,
        "safety_and_budget": {},
    }
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/runtime/test_retrieval_package.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/we_together/runtime/retrieval_package.py src/we_together/runtime/activation.py tests/runtime/test_retrieval_package.py
git commit -m "feat: add runtime retrieval package builder"
```

### Task 10: 集成 bootstrap 脚本

**Files:**
- Modify: `scripts/bootstrap.py`
- Test: `tests/db/test_bootstrap.py`

- [ ] **Step 1: 扩展失败测试**

```python
# tests/db/test_bootstrap.py
from pathlib import Path
from we_together.db.bootstrap import bootstrap_project


def test_bootstrap_project_creates_database_and_runtime_dirs(temp_project_dir):
    bootstrap_project(temp_project_dir)
    assert (temp_project_dir / "db" / "main.sqlite3").exists()
    assert (temp_project_dir / "data" / "raw").exists()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/db/test_bootstrap.py -q`
Expected: FAIL

- [ ] **Step 3: 写最小实现**

```python
# src/we_together/db/bootstrap.py
from pathlib import Path
from we_together.db.migrator import run_migrations


def bootstrap_project(root: Path) -> None:
    bootstrap_directories(root)
    db_path = root / "db" / "main.sqlite3"
    migrations_dir = root / "db" / "migrations"
    run_migrations(db_path, migrations_dir)
```

```python
# scripts/bootstrap.py
from pathlib import Path
from we_together.db.bootstrap import bootstrap_project


if __name__ == "__main__":
    bootstrap_project(Path.cwd())
    print("bootstrap complete")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/db/test_bootstrap.py tests/db/test_migrations.py tests/db/test_schema_constraints.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/we_together/db/bootstrap.py scripts/bootstrap.py tests/db/test_bootstrap.py
git commit -m "feat: wire bootstrap into sqlite initialization flow"
```

### Task 11: 全量验证

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/state/current-status.md`

- [ ] **Step 1: 更新 README 中的实现状态**

在 `README.md` 中追加一节：

```markdown
## 本地开发启动（规划）

第一阶段目标：

- SQLite 主库可初始化
- 基础迁移可执行
- narration importer 可运行
- 运行时检索包可生成
```

- [ ] **Step 2: 更新状态页**

在 `docs/superpowers/state/current-status.md` 中追加：

```markdown
- 已生成 Phase 1 implementation plan
```

- [ ] **Step 3: 跑全量测试**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/state/current-status.md
git commit -m "docs: align status with phase 1 implementation plan"
```

## Self-Review

### Spec Coverage

本计划覆盖了：

- Python 工程骨架
- SQLite 主库与迁移
- 核心 schema
- Event -> Patch 流
- Identity 融合基础
- narration importer
- 运行时检索包
- bootstrap 初始化

未覆盖但已明确留到后续计划：

- Feishu / DingTalk / Slack / WeChat 具体 importer 适配
- 更复杂的 patch 重放与 snapshot 导出
- 完整多人物激活传播算法优化

### Placeholder Scan

本计划未使用 TBD / TODO / “稍后实现”等占位写法。每个任务都给出文件路径、测试和命令。

### Type Consistency

本计划统一使用：

- `ImportResult`
- `ActivationState`
- `ResponseMode`
- `build_patch`
- `build_runtime_retrieval_package`

Plan complete and saved to `docs/superpowers/plans/2026-04-05-phase-1-kernel-implementation.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
