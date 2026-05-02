import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.runtime.sqlite_retrieval import invalidate_runtime_retrieval_cache


def create_group(
    db_path: Path,
    group_type: str,
    name: str,
    summary: str,
) -> str:
    group_id = f"group_{uuid.uuid4().hex}"
    now = datetime.now(UTC).isoformat()
    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO groups(
            group_id, group_type, name, summary, norms_summary,
            status, confidence, metadata_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            group_id,
            group_type,
            name,
            summary,
            None,
            "active",
            0.8,
            json.dumps({}, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    invalidate_runtime_retrieval_cache(db_path=db_path)
    return group_id


def add_group_member(
    db_path: Path,
    group_id: str,
    person_id: str,
    role_label: str,
) -> None:
    conn = connect(db_path)
    conn.execute(
        """
        INSERT OR IGNORE INTO group_members(
            group_id, person_id, role_label, joined_at, left_at, status, metadata_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?)
        """,
        (
            group_id,
            person_id,
            role_label,
            None,
            None,
            "active",
            json.dumps({}, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()
    invalidate_runtime_retrieval_cache(db_path=db_path)
