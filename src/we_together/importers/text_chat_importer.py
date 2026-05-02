import re
import uuid

from we_together.importers.base import ImportResult

LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+(?P<speaker>[^:：]+)[:：]\s*(?P<content>.+)$"
)


def import_text_chat(transcript: str, source_name: str) -> dict:
    evidence_id = f"evi_{uuid.uuid4().hex}"
    identity_candidates = []
    event_candidates = []
    seen_speakers = set()

    for line in transcript.splitlines():
        line = line.strip()
        if not line:
            continue
        match = LINE_RE.match(line)
        if not match:
            continue
        speaker = match.group("speaker").strip()
        timestamp = match.group("timestamp").strip()
        content = match.group("content").strip()
        if speaker not in seen_speakers:
            seen_speakers.add(speaker)
            identity_candidates.append(
                {
                    "candidate_id": f"idc_{uuid.uuid4().hex}",
                    "evidence_id": evidence_id,
                    "platform": "text_chat",
                    "external_id": speaker,
                    "display_name": speaker,
                    "aliases": [speaker],
                    "confidence": 0.8,
                }
            )
        event_candidates.append(
            {
                "candidate_id": f"evc_{uuid.uuid4().hex}",
                "evidence_id": evidence_id,
                "event_type": "message",
                "actor_candidates": [speaker],
                "time_hint": timestamp,
                "summary": content,
                "confidence": 0.8,
            }
        )

    result = ImportResult(
        raw_evidences=[
            {
                "evidence_id": evidence_id,
                "source_type": "text_chat",
                "source_platform": "manual",
                "source_locator": source_name,
                "content_type": "text",
                "raw_content": transcript,
                "normalized_text": transcript,
            }
        ],
        identity_candidates=identity_candidates,
        event_candidates=event_candidates,
        stats={
            "evidence_count": 1,
            "speaker_count": len(identity_candidates),
            "event_count": len(event_candidates),
        },
    )
    return result.__dict__
