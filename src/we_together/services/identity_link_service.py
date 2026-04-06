from datetime import UTC, datetime
import json
from pathlib import Path
import uuid

from we_together.db.connection import connect


def upsert_identity_link(
    db_path: Path,
    person_id: str,
    platform: str,
    external_id: str,
    display_name: str,
    confidence: float,
) -> str:
    identity_id = f"identity_{uuid.uuid5(uuid.NAMESPACE_URL, f'{platform}:{external_id}:{person_id}').hex}"
    now = datetime.now(UTC).isoformat()
    conn = connect(db_path)
    conn.execute(
        """
        INSERT OR IGNORE INTO identity_links(
            identity_id, person_id, platform, external_id, display_name,
            contact_json, org_json, match_method, confidence, is_user_confirmed,
            is_active, conflict_flags_json, metadata_json, created_at, updated_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            identity_id,
            person_id,
            platform,
            external_id,
            display_name,
            json.dumps({}, ensure_ascii=False),
            json.dumps({}, ensure_ascii=False),
            "direct_import",
            confidence,
            0,
            1,
            json.dumps([], ensure_ascii=False),
            json.dumps({}, ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()
    return identity_id
