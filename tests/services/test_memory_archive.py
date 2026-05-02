import sqlite3
from datetime import UTC, datetime, timedelta

from we_together.db.bootstrap import bootstrap_project
from we_together.services.memory_archive_service import (
    archive_cold_memories,
    list_cold_memories,
    restore_cold_memory,
)


def _insert_mem(db_path, mid, *, status="active", relevance=0.8, updated_offset_days=0):
    c = sqlite3.connect(db_path)
    updated = (datetime.now(UTC) - timedelta(days=updated_offset_days)).isoformat()
    c.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score, confidence,
           is_shared, status, metadata_json, created_at, updated_at)
           VALUES(?, 'shared_memory', ?, ?, 0.7, 1, ?, '{}', datetime('now'), ?)""",
        (mid, f"m {mid}", relevance, status, updated),
    )
    c.execute(
        "INSERT OR IGNORE INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('px','P','active',0.8,'{}',"
        "datetime('now'),datetime('now'))"
    )
    c.execute(
        "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
        "VALUES(?, 'person', 'px', NULL)",
        (mid,),
    )
    c.commit()
    c.close()


def test_archive_moves_inactive_to_cold(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _insert_mem(db_path, "m_old_inactive", status="inactive", updated_offset_days=200)
    _insert_mem(db_path, "m_active_fresh", status="active", updated_offset_days=1)

    result = archive_cold_memories(db_path, window_days=180)
    assert "m_old_inactive" in result["archived_ids"]
    assert "m_active_fresh" not in result["archived_ids"]

    cold = list_cold_memories(db_path)
    assert any(c["memory_id"] == "m_old_inactive" for c in cold)


def test_archive_low_relevance(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _insert_mem(db_path, "m_lowrel", status="active", relevance=0.05,
                updated_offset_days=200)

    result = archive_cold_memories(db_path, window_days=180, relevance_threshold=0.15)
    assert "m_lowrel" in result["archived_ids"]


def test_restore_cold_memory(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _insert_mem(db_path, "m_restore", status="inactive", updated_offset_days=200)

    archive_cold_memories(db_path, window_days=180)
    assert restore_cold_memory(db_path, "m_restore")

    c = sqlite3.connect(db_path)
    row = c.execute(
        "SELECT status FROM memories WHERE memory_id = 'm_restore'"
    ).fetchone()
    c.close()
    assert row is not None
    assert row[0] == "active"
