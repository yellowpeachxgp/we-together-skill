import uuid

from we_together.importers.base import ImportResult


def import_narration_text(text: str, source_name: str) -> dict:
    evidence_id = f"evi_{uuid.uuid4().hex}"
    result = ImportResult(
        raw_evidences=[
            {
                "evidence_id": evidence_id,
                "source_type": "narration",
                "source_platform": "manual",
                "source_locator": source_name,
                "content_type": "text",
                "raw_content": text,
                "normalized_text": text,
            }
        ],
        stats={"evidence_count": 1},
    )
    return result.__dict__
