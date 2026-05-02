# Ingestion Failure Path Implementation Plan

I'm using the writing-plans skill to create the implementation plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure that file and directory ingestion expose a deterministic failure contract for missing inputs and clarify how unsupported files are skipped.

**Architecture:** The ingestion services should validate the existence of the supplied path before attempting imports, and directory ingestion should track skipped files explicitly so downstream callers know which files were ignored.

**Tech Stack:** Python 3.11, `pathlib`, and `pytest` driven unit tests that exercise the four touched files.

---

### Task 1: File ingestion failure contract

**Files:**
- Modify: `src/we_together/services/file_ingestion_service.py:1-25`
- Modify: `tests/services/test_file_ingestion_service.py:1-50`

- [ ] **Step 1: Write the failing test**

```python
import pytest

def test_ingest_file_auto_raises_when_file_missing(temp_project_with_migrations):
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    missing = temp_project_with_migrations / "db" / "samples" / "missing.txt"
    with pytest.raises(FileNotFoundError) as excinfo:
        ingest_file_auto(db_path=db_path, file_path=missing)
    assert str(missing) in str(excinfo.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/services/test_file_ingestion_service.py::test_ingest_file_auto_raises_when_file_missing -vv`
Expected: FAIL because the service currently reads the path unguarded and no exception is raised.

- [ ] **Step 3: Write minimal implementation**

```python
def ingest_file_auto(db_path: Path, file_path: Path) -> dict:
    if not file_path.exists():
        raise FileNotFoundError(f"Cannot ingest file because {file_path} does not exist.")
    ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/services/test_file_ingestion_service.py::test_ingest_file_auto_raises_when_file_missing -vv`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add tests/services/test_file_ingestion_service.py src/we_together/services/file_ingestion_service.py
git commit -m "feat: enforce file existence before ingestion"
```

### Task 2: Directory ingestion failure + skip reporting

**Files:**
- Modify: `src/we_together/services/directory_ingestion_service.py:1-40`
- Modify: `tests/services/test_directory_ingestion_service.py:1-80`

- [ ] **Step 1: Write the failing tests**

```python
import pytest

def test_ingest_directory_raises_when_directory_missing(temp_project_with_migrations, tmp_path):
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    missing = tmp_path / "nonexistent"
    with pytest.raises(FileNotFoundError) as excinfo:
        ingest_directory(db_path=db_path, directory=missing)
    assert str(missing) in str(excinfo.value)

def test_ingest_directory_reports_skipped_unsupported_files(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    (tmp_path / "note.txt").write_text("a text file", encoding="utf-8")
    (tmp_path / "image.png").write_text("png bytes", encoding="utf-8")

    result = ingest_directory(db_path=db_path, directory=tmp_path)

    assert result["file_count"] == 1
    assert result["skipped_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/services/test_directory_ingestion_service.py::test_ingest_directory_raises_when_directory_missing tests/services/test_directory_ingestion_service.py::test_ingest_directory_reports_skipped_unsupported_files -vv`
Expected: FAIL because missing-directory handling and `skipped_count` tracking do not yet exist.

- [ ] **Step 3: Write minimal implementation**

```python
def ingest_directory(db_path: Path, directory: Path) -> dict:
    if not directory.exists():
        raise FileNotFoundError(f"Cannot ingest directory because {directory} does not exist.")

    imported = []
    skipped = 0
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            skipped += 1
            continue
        imported.append(ingest_file_auto(db_path=db_path, file_path=path))

    return {
        "file_count": len(imported),
        "skipped_count": skipped,
        "results": imported,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/services/test_directory_ingestion_service.py::test_ingest_directory_raises_when_directory_missing tests/services/test_directory_ingestion_service.py::test_ingest_directory_reports_skipped_unsupported_files -vv`
Expected: PASS

- [ ] **Step 5: Commit**

```
git add tests/services/test_directory_ingestion_service.py src/we_together/services/directory_ingestion_service.py
git commit -m "feat: add directory failure contract and skip reporting"
```

## Self-Review

- Spec coverage: Task 1 handles missing files with explicit exception, Task 2 handles missing directories and documents skip counts as required.
- Placeholder scan: every code block contains concrete code; there are no "TBD" markers.
- Type consistency: `skipped_count` is introduced alongside existing return shape and is referenced consistently in the tests defined above.
