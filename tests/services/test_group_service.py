import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.group_service import create_group, add_group_member


def test_create_group_and_add_members_persist_records(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    group_id = create_group(
        db_path=db_path,
        group_type="team",
        name="核心团队",
        summary="主开发小组",
    )
    add_group_member(
        db_path=db_path,
        group_id=group_id,
        person_id="person_alice",
        role_label="owner",
    )
    add_group_member(
        db_path=db_path,
        group_id=group_id,
        person_id="person_bob",
        role_label="member",
    )

    conn = sqlite3.connect(db_path)
    group_count = conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    member_count = conn.execute("SELECT COUNT(*) FROM group_members").fetchone()[0]
    conn.close()

    assert group_count == 1
    assert member_count == 2
