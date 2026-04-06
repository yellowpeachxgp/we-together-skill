import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.auto_ingestion_service import auto_ingest_text


def test_auto_ingest_text_uses_text_chat_path_for_timestamped_content(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    transcript = "2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n"
    result = auto_ingest_text(db_path=db_path, text=transcript, source_name="chat.txt")

    conn = sqlite3.connect(db_path)
    event_count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    conn.close()

    assert result["mode"] == "text_chat"
    assert event_count >= 2


def test_auto_ingest_text_uses_narration_path_for_plain_text(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    result = auto_ingest_text(
        db_path=db_path,
        text="小王和小李以前是同事，现在还是朋友。",
        source_name="manual-note",
    )

    assert result["mode"] == "narration"
