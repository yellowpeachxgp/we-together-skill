import sqlite3

from we_together.db.bootstrap import bootstrap_project


def test_bootstrap_project_loads_seed_enums(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT entity_type, entity_id, tag FROM entity_tags ORDER BY entity_type, entity_id, tag"
    ).fetchall()
    conn.close()

    assert ("scene_enum", "private_chat", "scene_type") in rows
    assert ("activation_enum", "explicit", "activation_state") in rows


def test_bootstrap_project_seed_loading_is_idempotent(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    total_rows = conn.execute("SELECT COUNT(*) FROM entity_tags").fetchone()[0]
    distinct_rows = conn.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT entity_type, entity_id, tag, weight FROM entity_tags)"
    ).fetchone()[0]
    conn.close()

    assert total_rows == distinct_rows
