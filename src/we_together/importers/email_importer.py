import re
import uuid
from email import policy
from email.parser import BytesParser
from pathlib import Path

from we_together.importers.base import ImportResult


def _extract_display_name(from_header: str) -> str:
    name_part = from_header.split("<", 1)[0].strip().strip('"')
    if name_part:
        return name_part
    email_match = re.search(r"<([^>]+)>", from_header)
    if email_match:
        return email_match.group(1).split("@", 1)[0]
    return from_header.strip()


def import_email_file(email_path: Path) -> dict:
    with email_path.open("rb") as fh:
        message = BytesParser(policy=policy.default).parse(fh)

    from_header = str(message.get("From", ""))
    subject = str(message.get("Subject", ""))
    body = message.get_body(preferencelist=("plain",))
    text = body.get_content() if body else ""
    display_name = _extract_display_name(from_header)
    evidence_id = f"evi_{uuid.uuid4().hex}"

    result = ImportResult(
        raw_evidences=[
            {
                "evidence_id": evidence_id,
                "source_type": "email",
                "source_platform": "file",
                "source_locator": str(email_path),
                "content_type": "email",
                "raw_content": text,
                "normalized_text": text,
            }
        ],
        identity_candidates=[
            {
                "candidate_id": f"idc_{uuid.uuid4().hex}",
                "evidence_id": evidence_id,
                "platform": "email",
                "external_id": from_header,
                "display_name": display_name,
                "aliases": [display_name],
                "confidence": 0.9,
            }
        ],
        event_candidates=[
            {
                "candidate_id": f"evc_{uuid.uuid4().hex}",
                "evidence_id": evidence_id,
                "event_type": "email",
                "actor_candidates": [display_name],
                "time_hint": str(message.get("Date", "")),
                "summary": f"{subject}: {text.strip()}",
                "confidence": 0.85,
            }
        ],
        stats={"evidence_count": 1, "event_count": 1, "speaker_count": 1},
    )
    return result.__dict__
