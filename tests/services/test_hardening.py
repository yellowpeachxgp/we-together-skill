from pathlib import Path

import pytest

from we_together.db.bootstrap import bootstrap_project
from we_together.db.schema_version import check_schema_version
from we_together.errors import SchemaVersionError, WeTogetherError
from we_together.services.cache_warmer import warm_retrieval_cache
from we_together.services.patch_batch import apply_patches_bulk
from we_together.services.patch_service import build_patch


def test_schema_version_check_on_fresh_db(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    r = check_schema_version(
        temp_project_with_migrations / "db" / "main.sqlite3",
        temp_project_with_migrations / "db" / "migrations",
    )
    assert r["latest_applied"] is not None
    assert r["pending"] == []


def test_schema_version_detects_missing_local_migration(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    # 指向一个空的 migrations 目录 → 应触发 SchemaVersionError
    empty_dir = tmp_path / "empty_migrations"
    empty_dir.mkdir()
    with pytest.raises(SchemaVersionError):
        check_schema_version(db_path, empty_dir)


def test_apply_patches_bulk_success(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    patches = [
        build_patch(
            source_event_id=f"src_{i}", target_type="memory", target_id=f"m_b_{i}",
            operation="create_memory",
            payload={"memory_id": f"m_b_{i}", "memory_type": "shared_memory",
                     "summary": f"s {i}", "relevance_score": 0.5, "confidence": 0.5,
                     "is_shared": 1, "status": "active", "metadata_json": {}},
            confidence=0.5, reason="bulk test",
        )
        for i in range(3)
    ]
    result = apply_patches_bulk(db_path, patches)
    assert result["applied_count"] == 3
    assert result["failed_count"] == 0


def test_apply_patches_bulk_stops_on_error(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    bad_patch = build_patch(
        source_event_id="bad", target_type="memory", target_id="x",
        operation="nonexistent_operation", payload={}, confidence=0.5, reason="bad",
    )
    result = apply_patches_bulk(db_path, [bad_patch], stop_on_error=True)
    assert result["failed_count"] == 1
    assert result["applied_count"] == 0


def test_warm_retrieval_cache(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    r = warm_retrieval_cache(db_path)
    # 空数据库没有 scene；返回 warmed=0 + 无错误
    assert r["warmed_count"] == 0
    assert r["errors"] == []
