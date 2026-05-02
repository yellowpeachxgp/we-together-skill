"""Proactive prefs：per-person 主动图谱控制。"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect


def _now() -> str:
    return datetime.now(UTC).isoformat()


def set_mute(db_path: Path, person_id: str, *, mute: bool = True) -> None:
    conn = connect(db_path)
    conn.execute(
        """INSERT INTO proactive_prefs(person_id, mute, trigger_consents, updated_at)
           VALUES(?, ?, '{}', ?)
           ON CONFLICT(person_id) DO UPDATE SET mute=excluded.mute, updated_at=excluded.updated_at""",
        (person_id, 1 if mute else 0, _now()),
    )
    conn.commit(); conn.close()


def set_consent(db_path: Path, person_id: str, trigger_name: str, consent: bool) -> None:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT trigger_consents FROM proactive_prefs WHERE person_id = ?",
        (person_id,),
    ).fetchone()
    consents = json.loads(row["trigger_consents"]) if row else {}
    consents[trigger_name] = consent
    conn.execute(
        """INSERT INTO proactive_prefs(person_id, mute, trigger_consents, updated_at)
           VALUES(?, 0, ?, ?)
           ON CONFLICT(person_id) DO UPDATE SET
               trigger_consents=excluded.trigger_consents,
               updated_at=excluded.updated_at""",
        (person_id, json.dumps(consents), _now()),
    )
    conn.commit(); conn.close()


def is_allowed(db_path: Path, person_id: str, trigger_name: str) -> bool:
    conn = connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT mute, trigger_consents FROM proactive_prefs WHERE person_id = ?",
        (person_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return True  # 无 pref → 默认允许
    if row["mute"]:
        return False
    consents = json.loads(row["trigger_consents"] or "{}")
    # 显式 consent=False 阻断；否则默认允许
    return consents.get(trigger_name, True)
