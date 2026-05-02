"""LLM 驱动的候选抽取。

与硬编码规则 `infer_narration_patches` 的区别：
  - 规则式：看关键词 → 输出固定 patch
  - LLM 式：把文本和 schema 喂给 LLM → 得到 {identity_candidates, event_candidates,
    relation_clues} → 写 candidate 层 → 交给 fusion_service 落图谱

MockLLMClient 默认 scripted，生产切换 anthropic / openai_compat。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from we_together.db.connection import connect
from we_together.llm.client import LLMClient, LLMMessage
from we_together.services.candidate_store import (
    write_event_candidate,
    write_identity_candidate,
    write_relation_clue,
)


EXTRACTION_SCHEMA = {
    "identity_candidates": [
        {
            "display_name": "str (必填)",
            "platform": "str | null",
            "external_id": "str | null",
            "confidence": "float 0..1",
        }
    ],
    "relation_clues": [
        {
            "participants": ["display_name_a", "display_name_b"],
            "core_type_hint": "friendship | work | family | intimacy | authority | ...",
            "custom_label_hint": "str | null",
            "strength_hint": "float 0..1",
            "confidence": "float 0..1",
            "summary": "str",
        }
    ],
    "event_candidates": [
        {
            "event_type": "str",
            "actor_display_names": ["display_name_a"],
            "summary": "str",
            "confidence": "float 0..1",
            "time_hint": "iso8601 | null",
        }
    ],
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _create_import_job(conn: sqlite3.Connection, source_name: str) -> str:
    job_id = f"job_{uuid.uuid4().hex[:14]}"
    conn.execute(
        """
        INSERT INTO import_jobs(
            import_job_id, source_type, source_platform, status,
            stats_json, started_at, finished_at
        ) VALUES(?, 'llm_extraction', ?, 'completed', '{}', ?, ?)
        """,
        (job_id, source_name, _now(), _now()),
    )
    return job_id


def _create_evidence(conn: sqlite3.Connection, job_id: str, text: str, source_name: str) -> str:
    eid = f"evd_{uuid.uuid4().hex[:14]}"
    conn.execute(
        """
        INSERT INTO raw_evidences(
            evidence_id, import_job_id, source_type, source_platform,
            content_type, normalized_text, created_at
        ) VALUES(?, ?, 'llm_extraction', ?, 'text', ?, ?)
        """,
        (eid, job_id, source_name, text, _now()),
    )
    return eid


def _build_extraction_prompt(text: str) -> list[LLMMessage]:
    return [
        LLMMessage(
            role="system",
            content=(
                "你是社会图谱抽取器。输入一段中文自然语言，"
                "抽取其中涉及的人物、关系、事件。严格按照给定 JSON schema 返回，"
                "禁止编造文本中没有的人或关系。每个字段给出合理置信度（0..1）。"
            ),
        ),
        LLMMessage(
            role="user",
            content=f"文本:\n{text}\n\n请返回 JSON。"
        ),
    ]


def extract_candidates_from_text(
    db_path: Path,
    *,
    text: str,
    source_name: str,
    llm_client: LLMClient,
) -> dict:
    """抽取候选并写入 candidate 层。返回统计摘要。

    不会自动调 fusion：调用方决定何时归并。
    """
    conn = connect(db_path)
    job_id = _create_import_job(conn, source_name)
    evidence_id = _create_evidence(conn, job_id, text, source_name)
    conn.commit()
    conn.close()

    messages = _build_extraction_prompt(text)
    try:
        payload = llm_client.chat_json(messages, schema_hint=EXTRACTION_SCHEMA)
    except Exception as exc:
        return {
            "job_id": job_id,
            "evidence_id": evidence_id,
            "error": str(exc),
            "identity_candidates": 0,
            "relation_clues": 0,
            "event_candidates": 0,
        }

    # 写 identity_candidates 并记下 display_name → candidate_id 映射
    name_to_cid: dict[str, str] = {}
    for ic in payload.get("identity_candidates", []):
        display_name = ic.get("display_name")
        if not display_name:
            continue
        cid = write_identity_candidate(
            db_path=db_path,
            evidence_id=evidence_id,
            platform=ic.get("platform"),
            external_id=ic.get("external_id"),
            display_name=display_name,
            confidence=float(ic.get("confidence", 0.5)),
            import_job_id=job_id,
        )
        name_to_cid[display_name] = cid

    # 写 relation_clues（participant display_names → candidate_ids）
    rel_count = 0
    for rc in payload.get("relation_clues", []):
        participants = rc.get("participants", [])
        cand_ids = [name_to_cid[n] for n in participants if n in name_to_cid]
        if len(cand_ids) < 2:
            continue
        write_relation_clue(
            db_path=db_path,
            evidence_id=evidence_id,
            participant_candidate_ids=cand_ids,
            core_type_hint=rc.get("core_type_hint"),
            custom_label_hint=rc.get("custom_label_hint"),
            strength_hint=rc.get("strength_hint"),
            summary=rc.get("summary"),
            confidence=float(rc.get("confidence", 0.5)),
            import_job_id=job_id,
        )
        rel_count += 1

    # 写 event_candidates
    evt_count = 0
    for ec in payload.get("event_candidates", []):
        actor_cids = [name_to_cid[n] for n in ec.get("actor_display_names", []) if n in name_to_cid]
        write_event_candidate(
            db_path=db_path,
            evidence_id=evidence_id,
            event_type=ec.get("event_type"),
            actor_candidate_ids=actor_cids,
            summary=ec.get("summary"),
            time_hint=ec.get("time_hint"),
            confidence=float(ec.get("confidence", 0.5)),
            import_job_id=job_id,
        )
        evt_count += 1

    return {
        "job_id": job_id,
        "evidence_id": evidence_id,
        "identity_candidates": len(name_to_cid),
        "relation_clues": rel_count,
        "event_candidates": evt_count,
    }
