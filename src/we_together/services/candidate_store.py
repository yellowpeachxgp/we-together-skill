"""统一候选中间层存储 API。

导入器产出的候选对象先落此层，再由 fusion_service 聚合为 patch。
"""
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect


def _tier_from_score(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def write_identity_candidate(
    db_path: Path,
    *,
    evidence_id: str,
    platform: str | None = None,
    external_id: str | None = None,
    display_name: str | None = None,
    aliases: list[str] | None = None,
    contact: dict | None = None,
    org: dict | None = None,
    match_hints: dict | None = None,
    confidence: float,
    import_job_id: str | None = None,
) -> str:
    candidate_id = _new_id("idc")
    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO identity_candidates(
            candidate_id, evidence_id, import_job_id, platform, external_id,
            display_name, aliases_json, contact_json, org_json, match_hints_json,
            confidence, confidence_tier, status, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """,
        (
            candidate_id,
            evidence_id,
            import_job_id,
            platform,
            external_id,
            display_name,
            json.dumps(aliases or [], ensure_ascii=False),
            json.dumps(contact or {}, ensure_ascii=False),
            json.dumps(org or {}, ensure_ascii=False),
            json.dumps(match_hints or {}, ensure_ascii=False),
            confidence,
            _tier_from_score(confidence),
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    return candidate_id


def write_event_candidate(
    db_path: Path,
    *,
    evidence_id: str,
    event_type: str | None = None,
    actor_candidate_ids: list[str] | None = None,
    target_candidate_ids: list[str] | None = None,
    group_candidate_ids: list[str] | None = None,
    scene_hint: str | None = None,
    time_hint: str | None = None,
    summary: str | None = None,
    confidence: float,
    import_job_id: str | None = None,
) -> str:
    candidate_id = _new_id("evc")
    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO event_candidates(
            candidate_id, evidence_id, import_job_id, event_type,
            actor_candidate_ids_json, target_candidate_ids_json,
            group_candidate_ids_json, scene_hint, time_hint, summary,
            confidence, confidence_tier, status, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """,
        (
            candidate_id,
            evidence_id,
            import_job_id,
            event_type,
            json.dumps(actor_candidate_ids or [], ensure_ascii=False),
            json.dumps(target_candidate_ids or [], ensure_ascii=False),
            json.dumps(group_candidate_ids or [], ensure_ascii=False),
            scene_hint,
            time_hint,
            summary,
            confidence,
            _tier_from_score(confidence),
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    return candidate_id


def write_facet_candidate(
    db_path: Path,
    *,
    evidence_id: str,
    facet_type: str,
    facet_key: str | None = None,
    facet_value: str | None = None,
    target_identity_candidate_ids: list[str] | None = None,
    target_person_id: str | None = None,
    confidence: float,
    reason: str | None = None,
    import_job_id: str | None = None,
) -> str:
    candidate_id = _new_id("fcc")
    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO facet_candidates(
            candidate_id, evidence_id, import_job_id,
            target_identity_candidate_ids_json, target_person_id,
            facet_type, facet_key, facet_value,
            confidence, confidence_tier, reason, status, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """,
        (
            candidate_id,
            evidence_id,
            import_job_id,
            json.dumps(target_identity_candidate_ids or [], ensure_ascii=False),
            target_person_id,
            facet_type,
            facet_key,
            facet_value,
            confidence,
            _tier_from_score(confidence),
            reason,
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    return candidate_id


def write_relation_clue(
    db_path: Path,
    *,
    evidence_id: str,
    participant_candidate_ids: list[str] | None = None,
    core_type_hint: str | None = None,
    custom_label_hint: str | None = None,
    directionality_hint: str | None = None,
    strength_hint: float | None = None,
    stability_hint: float | None = None,
    summary: str | None = None,
    confidence: float,
    import_job_id: str | None = None,
) -> str:
    clue_id = _new_id("rlc")
    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO relation_clues(
            clue_id, evidence_id, import_job_id,
            participant_candidate_ids_json, core_type_hint, custom_label_hint,
            directionality_hint, strength_hint, stability_hint, summary,
            confidence, confidence_tier, status, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """,
        (
            clue_id,
            evidence_id,
            import_job_id,
            json.dumps(participant_candidate_ids or [], ensure_ascii=False),
            core_type_hint,
            custom_label_hint,
            directionality_hint,
            strength_hint,
            stability_hint,
            summary,
            confidence,
            _tier_from_score(confidence),
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    return clue_id


def write_group_clue(
    db_path: Path,
    *,
    evidence_id: str,
    group_type_hint: str | None = None,
    group_name_hint: str | None = None,
    member_candidate_ids: list[str] | None = None,
    role_hints: dict | None = None,
    norm_hints: dict | None = None,
    confidence: float,
    import_job_id: str | None = None,
) -> str:
    clue_id = _new_id("grc")
    conn = connect(db_path)
    conn.execute(
        """
        INSERT INTO group_clues(
            clue_id, evidence_id, import_job_id,
            group_type_hint, group_name_hint, member_candidate_ids_json,
            role_hints_json, norm_hints_json,
            confidence, confidence_tier, status, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        """,
        (
            clue_id,
            evidence_id,
            import_job_id,
            group_type_hint,
            group_name_hint,
            json.dumps(member_candidate_ids or [], ensure_ascii=False),
            json.dumps(role_hints or {}, ensure_ascii=False),
            json.dumps(norm_hints or {}, ensure_ascii=False),
            confidence,
            _tier_from_score(confidence),
            _now(),
        ),
    )
    conn.commit()
    conn.close()
    return clue_id


def list_open_candidates(db_path: Path, table: str, limit: int = 100) -> list[dict]:
    """通用列出函数（fusion_service 使用）。"""
    allowed = {
        "identity_candidates",
        "event_candidates",
        "facet_candidates",
        "relation_clues",
        "group_clues",
    }
    if table not in allowed:
        raise ValueError(f"Unknown candidate table: {table}")
    import sqlite3 as _sqlite3

    conn = _sqlite3.connect(db_path)
    conn.row_factory = _sqlite3.Row
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE status = 'open' ORDER BY created_at ASC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_candidate_linked(
    db_path: Path,
    table: str,
    candidate_id_col: str,
    candidate_id: str,
    *,
    link_col: str,
    link_id: str,
) -> None:
    """在候选被 fusion 落地为正式对象后，更新 status='linked' 和 linked_* 列。"""
    allowed = {
        "identity_candidates": ("candidate_id", "linked_person_id"),
        "event_candidates": ("candidate_id", "linked_event_id"),
        "relation_clues": ("clue_id", "linked_relation_id"),
        "group_clues": ("clue_id", "linked_group_id"),
    }
    if table not in allowed:
        raise ValueError(f"mark_candidate_linked unsupported for: {table}")
    conn = connect(db_path)
    conn.execute(
        f"UPDATE {table} SET status = 'linked', {link_col} = ? WHERE {candidate_id_col} = ?",
        (link_id, candidate_id),
    )
    conn.commit()
    conn.close()
