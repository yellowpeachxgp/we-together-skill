from datetime import UTC, datetime


def build_snapshot(
    snapshot_id: str,
    based_on_snapshot_id: str | None,
    trigger_event_id: str | None,
    summary: str,
    graph_hash: str,
) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "based_on_snapshot_id": based_on_snapshot_id,
        "trigger_event_id": trigger_event_id,
        "summary": summary,
        "graph_hash": graph_hash,
        "created_at": datetime.now(UTC).isoformat(),
    }
