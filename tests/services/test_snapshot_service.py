from we_together.services.snapshot_service import build_snapshot


def test_build_snapshot_creates_structured_snapshot():
    snapshot = build_snapshot(
        snapshot_id="snap_1",
        based_on_snapshot_id=None,
        trigger_event_id="evt_1",
        summary="after import",
        graph_hash="hash_123",
    )

    assert snapshot["snapshot_id"] == "snap_1"
    assert snapshot["trigger_event_id"] == "evt_1"
    assert snapshot["graph_hash"] == "hash_123"
