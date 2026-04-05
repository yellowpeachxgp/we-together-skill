from datetime import UTC, datetime
import uuid


def build_patch(
    source_event_id: str,
    target_type: str,
    target_id: str | None,
    operation: str,
    payload: dict,
    confidence: float,
    reason: str,
) -> dict:
    return {
        "patch_id": f"patch_{uuid.uuid4().hex}",
        "source_event_id": source_event_id,
        "target_type": target_type,
        "target_id": target_id,
        "operation": operation,
        "payload_json": payload,
        "confidence": confidence,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
        "applied_at": None,
    }
