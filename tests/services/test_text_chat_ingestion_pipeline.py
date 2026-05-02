import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.ingestion_service import ingest_text_chat


def test_ingest_text_chat_creates_people_and_multiple_events(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    transcript = """2026-04-06 23:10 小王: 今天好累
2026-04-06 23:11 小李: 早点休息
"""

    result = ingest_text_chat(
        db_path=db_path,
        transcript=transcript,
        source_name="chat.txt",
    )

    conn = sqlite3.connect(db_path)
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    identity_count = conn.execute("SELECT COUNT(*) FROM identity_links").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    snapshot_entity_count = conn.execute("SELECT COUNT(*) FROM snapshot_entities").fetchone()[0]
    relation_row = conn.execute(
        "SELECT core_type, custom_label, summary FROM relations ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()

    assert result["import_job_id"].startswith("import_")
    assert person_count >= 2
    assert identity_count >= 2
    assert event_count >= 2
    assert memory_count >= 1
    assert snapshot_entity_count >= 4
    assert relation_row[0] == "interaction"
    assert relation_row[1] == "聊天关系"
    assert "小王" in relation_row[2] or "小李" in relation_row[2]


def test_ingest_text_chat_links_events_to_participants(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    transcript = """2026-04-06 23:10 小王: 今天好累
2026-04-06 23:11 小李: 早点休息
"""

    ingest_text_chat(
        db_path=db_path,
        transcript=transcript,
        source_name="chat.txt",
    )

    conn = sqlite3.connect(db_path)
    participant_rows = conn.execute(
        """
        SELECT e.summary, p.primary_name, ep.participant_role
        FROM event_participants ep
        JOIN events e ON e.event_id = ep.event_id
        JOIN persons p ON p.person_id = ep.person_id
        ORDER BY e.timestamp, p.primary_name
        """
    ).fetchall()
    conn.close()

    assert participant_rows == [
        ("今天好累", "小王", "speaker"),
        ("早点休息", "小李", "speaker"),
    ]


def test_ingest_text_chat_applies_inferred_patches_and_entity_links(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    transcript = """2026-04-06 23:10 小王: 今天好累
2026-04-06 23:11 小李: 早点休息
"""

    ingest_text_chat(
        db_path=db_path,
        transcript=transcript,
        source_name="chat.txt",
    )

    conn = sqlite3.connect(db_path)
    patch_operations = {row[0] for row in conn.execute("SELECT operation FROM patches").fetchall()}
    entity_link_count = conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    person_state_count = conn.execute(
        "SELECT COUNT(*) FROM states WHERE scope_type = 'person'"
    ).fetchone()[0]
    conn.close()

    assert "create_memory" in patch_operations
    assert "link_entities" in patch_operations
    assert "update_state" in patch_operations
    assert entity_link_count >= 1
    assert person_state_count >= 1


def test_ingest_text_chat_applies_inferred_patches_and_relation_targets(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    transcript = """2026-04-06 23:10 小王: 今天好累
2026-04-06 23:11 小李: 早点休息
"""

    ingest_text_chat(
        db_path=db_path,
        transcript=transcript,
        source_name="chat.txt",
    )

    conn = sqlite3.connect(db_path)
    patch_operations = {
        row[0] for row in conn.execute("SELECT operation FROM patches").fetchall()
    }
    entity_link_count = conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0]
    relation_target_count = conn.execute(
        "SELECT COUNT(*) FROM event_targets WHERE target_type = 'relation'"
    ).fetchone()[0]
    conn.close()

    assert "create_memory" in patch_operations
    assert "link_entities" in patch_operations
    assert entity_link_count >= 1
    assert relation_target_count >= 1
