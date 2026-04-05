from datetime import UTC, datetime
import json
import uuid
from pathlib import Path

from we_together.db.connection import connect


def create_scene(
    db_path: Path,
    scene_type: str,
    scene_summary: str,
    environment: dict,
) -> str:
    scene_id = f"scene_{uuid.uuid4().hex}"
    now = datetime.now(UTC).isoformat()
    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO scenes(
            scene_id, scene_type, group_id, trigger_event_id, scene_summary,
            location_scope, channel_scope, visibility_scope, time_scope, role_scope,
            access_scope, privacy_scope, activation_barrier, environment_json,
            status, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scene_id,
            scene_type,
            None,
            None,
            scene_summary,
            environment.get("location_scope"),
            environment.get("channel_scope"),
            environment.get("visibility_scope"),
            environment.get("time_scope"),
            environment.get("role_scope"),
            environment.get("access_scope"),
            environment.get("privacy_scope"),
            environment.get("activation_barrier"),
            json.dumps(environment, ensure_ascii=False),
            "active",
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return scene_id


def add_scene_participant(
    db_path: Path,
    scene_id: str,
    person_id: str,
    activation_state: str,
    activation_score: float,
    is_speaking: bool,
) -> None:
    now = datetime.now(UTC).isoformat()
    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO scene_participants(
            scene_id, person_id, activation_score, activation_state,
            is_speaking, reason_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            scene_id,
            person_id,
            activation_score,
            activation_state,
            1 if is_speaking else 0,
            json.dumps({}, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
