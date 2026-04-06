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
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()

    assert result["import_job_id"].startswith("import_")
    assert person_count >= 2
    assert event_count >= 2
