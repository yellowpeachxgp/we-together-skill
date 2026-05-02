from __future__ import annotations

import json
import re
from pathlib import Path

from we_together.packaging.codex_skill_support import DEFAULT_CODEX_SKILL_FAMILY

GENERIC_SKILL_MESSAGE_MARKERS = (
    "技能里要求",
    "本地运行时映射",
    "local-runtime",
    "local runtime",
)


def _default_skill_names() -> list[str]:
    return list(DEFAULT_CODEX_SKILL_FAMILY.keys())


def _empty_skill_hits() -> dict:
    return {
        "path_reads": [],
        "local_runtime_reads": [],
        "prompt_reads": [],
        "reference_reads": [],
        "messages": [],
    }


def _iter_session_records(session_path: Path):
    try:
        with session_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return


def _extract_read_paths(record: dict) -> list[str]:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return []
    if payload.get("type") != "exec_command_end":
        return []

    paths: list[str] = []
    for item in payload.get("parsed_cmd", []):
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if isinstance(path, str) and path:
            paths.append(path)
    return paths


def _extract_agent_message(record: dict) -> str | None:
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    if record.get("type") != "event_msg":
        return None
    if payload.get("type") != "agent_message":
        return None
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return None
    return message


def _match_skill_path(path: str, skill_names: list[str]) -> tuple[str, str] | None:
    for skill_name in skill_names:
        marker = f"/.codex/skills/{skill_name}/"
        if marker in path:
            rel_path = path.split(marker, 1)[1]
            return skill_name, rel_path
    return None


def _message_mentions_skill(message: str, skill_name: str) -> bool:
    pattern = re.compile(
        rf"(?<![A-Za-z0-9_-]){re.escape(skill_name)}(?![A-Za-z0-9_-])"
    )
    return bool(pattern.search(message))


def inspect_codex_session_for_skills(
    session_path: Path,
    *,
    skill_names: list[str] | None = None,
) -> dict:
    session_path = Path(session_path).expanduser().resolve()
    selected_skills = list(skill_names or _default_skill_names())
    hits_by_skill = {skill_name: _empty_skill_hits() for skill_name in selected_skills}
    agent_messages: list[dict] = []
    session_id: str | None = None
    cwd: str | None = None
    record_count = 0

    for record in _iter_session_records(session_path):
        record_count += 1
        payload = record.get("payload")
        if (
            session_id is None
            and record.get("type") == "session_meta"
            and isinstance(payload, dict)
        ):
            maybe_id = payload.get("id")
            maybe_cwd = payload.get("cwd")
            if isinstance(maybe_id, str) and maybe_id:
                session_id = maybe_id
            if isinstance(maybe_cwd, str) and maybe_cwd:
                cwd = maybe_cwd

        for path in _extract_read_paths(record):
            matched = _match_skill_path(path, selected_skills)
            if matched is None:
                continue
            skill_name, rel_path = matched
            evidence = {
                "timestamp": record.get("timestamp"),
                "path": path,
                "rel_path": rel_path,
            }
            hits = hits_by_skill[skill_name]
            hits["path_reads"].append(evidence)
            if rel_path == "references/local-runtime.md":
                hits["local_runtime_reads"].append(evidence)
            elif rel_path.startswith("prompts/"):
                hits["prompt_reads"].append(evidence)
            elif rel_path.startswith("references/"):
                hits["reference_reads"].append(evidence)

        message = _extract_agent_message(record)
        if message:
            agent_messages.append(
                {
                    "timestamp": record.get("timestamp"),
                    "message": message,
                }
            )

    path_matched_skills = {
        skill_name
        for skill_name, hits in hits_by_skill.items()
        if hits["path_reads"]
    }
    for item in agent_messages:
        normalized_message = item["message"].strip()
        explicit_matches = [
            skill_name
            for skill_name in selected_skills
            if normalized_message != skill_name
            and _message_mentions_skill(item["message"], skill_name)
        ]
        if explicit_matches:
            for skill_name in explicit_matches:
                hits_by_skill[skill_name]["messages"].append(item)
            continue

        if (
            len(path_matched_skills) == 1
            and any(marker in item["message"] for marker in GENERIC_SKILL_MESSAGE_MARKERS)
        ):
            only_skill = next(iter(path_matched_skills))
            hits_by_skill[only_skill]["messages"].append(item)

    matched_skills = sorted(
        skill_name
        for skill_name, hits in hits_by_skill.items()
        if any(hits[field] for field in hits)
    )
    return {
        "session_path": str(session_path),
        "session_id": session_id,
        "cwd": cwd,
        "record_count": record_count,
        "matched": bool(matched_skills),
        "matched_skills": matched_skills,
        "hits_by_skill": hits_by_skill,
    }


def collect_codex_skill_evidence(
    session_root: Path,
    *,
    skill_names: list[str] | None = None,
    limit: int | None = None,
) -> dict:
    session_root = Path(session_root).expanduser().resolve()
    selected_skills = list(skill_names or _default_skill_names())
    session_paths = sorted(session_root.rglob("*.jsonl")) if session_root.exists() else []
    if limit is not None and limit > 0:
        session_paths = session_paths[-limit:]

    sessions: list[dict] = []
    hits_by_skill = {
        skill_name: {
            "sessions": 0,
            "path_reads": 0,
            "local_runtime_reads": 0,
            "prompt_reads": 0,
            "reference_reads": 0,
            "messages": 0,
        }
        for skill_name in selected_skills
    }

    for session_path in session_paths:
        report = inspect_codex_session_for_skills(
            session_path,
            skill_names=selected_skills,
        )
        if not report["matched"]:
            continue
        sessions.append(report)
        for skill_name in report["matched_skills"]:
            evidence = report["hits_by_skill"][skill_name]
            hits_by_skill[skill_name]["sessions"] += 1
            hits_by_skill[skill_name]["path_reads"] += len(evidence["path_reads"])
            hits_by_skill[skill_name]["local_runtime_reads"] += len(
                evidence["local_runtime_reads"]
            )
            hits_by_skill[skill_name]["prompt_reads"] += len(evidence["prompt_reads"])
            hits_by_skill[skill_name]["reference_reads"] += len(
                evidence["reference_reads"]
            )
            hits_by_skill[skill_name]["messages"] += len(evidence["messages"])

    return {
        "ok": bool(sessions),
        "session_root": str(session_root),
        "skills": selected_skills,
        "scanned_sessions": len(session_paths),
        "matched_sessions": len(sessions),
        "hits_by_skill": hits_by_skill,
        "sessions": sessions,
    }
