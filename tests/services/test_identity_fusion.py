import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.identity_fusion_service import score_candidates, find_and_merge_duplicates


def test_score_candidates_prefers_strong_match():
    score = score_candidates(
        left={"platform": "email", "external_id": "a@example.com", "display_name": "Alice"},
        right={
            "platform": "email",
            "external_id": "a@example.com",
            "display_name": "Alice Zhang",
        },
    )
    assert score >= 0.9


def test_find_and_merge_duplicates_auto_merges(temp_project_with_migrations):
    """从不同来源导入同名人物后，find_and_merge_duplicates 应自动合并。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO persons(
            person_id, primary_name, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
        """,
        [("person_dup_a", "小明"), ("person_dup_b", "小明")],
    )
    conn.executemany(
        """
        INSERT INTO identity_links(
            identity_id, person_id, platform, external_id, display_name, confidence,
            is_user_confirmed, is_active, metadata_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, 0.8, 0, 1, '{}', datetime('now'), datetime('now'))
        """,
        [
            ("id_dup_a", "person_dup_a", "wechat", "xm_wx", "小明"),
            ("id_dup_b", "person_dup_b", "email", "xm@a.com", "小明"),
        ],
    )
    conn.commit()
    conn.close()

    result = find_and_merge_duplicates(db_path)

    assert result["merged_count"] >= 1

    conn = sqlite3.connect(db_path)
    active_persons = conn.execute(
        "SELECT person_id FROM persons WHERE primary_name = '小明' AND status = 'active'",
    ).fetchall()
    merged_persons = conn.execute(
        "SELECT person_id FROM persons WHERE primary_name = '小明' AND status = 'merged'",
    ).fetchall()
    conn.close()

    assert len(active_persons) == 1
    assert len(merged_persons) == 1
