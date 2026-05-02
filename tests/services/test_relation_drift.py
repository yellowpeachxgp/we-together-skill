from datetime import UTC, datetime, timedelta
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.relation_drift_service import drift_relations


def _seed_relation_with_events(db_path, relation_id, strength, summaries_with_offsets):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO relations(
            relation_id, core_type, custom_label, summary, directionality,
            strength, stability, visibility, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, 'friendship', '朋友', '', 'bidirectional',
                 ?, 0.5, 'known', 'active', 0.7, '{}', datetime('now'), datetime('now'))
        """,
        (relation_id, strength),
    )
    now = datetime.now(UTC)
    for i, (summary, offset_days) in enumerate(summaries_with_offsets):
        eid = f"evt_{relation_id}_{i}"
        ts = (now - timedelta(days=offset_days)).isoformat()
        conn.execute(
            """
            INSERT INTO events(
                event_id, event_type, source_type, timestamp, summary, visibility_level,
                confidence, is_structured, raw_evidence_refs_json, metadata_json, created_at
            ) VALUES(?, 'dialogue_event', 'manual', ?, ?, 'visible', 0.8, 0, '[]', '{}', datetime('now'))
            """,
            (eid, ts, summary),
        )
        conn.execute(
            """
            INSERT INTO event_targets(event_id, target_type, target_id, impact_hint)
            VALUES(?, 'relation', ?, 'test')
            """,
            (eid, relation_id),
        )
    conn.commit()
    conn.close()


def test_drift_no_events_decays_strength(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_with_events(db_path, "rel_quiet", strength=0.8, summaries_with_offsets=[])

    result = drift_relations(db_path, window_days=30)
    assert result["drifted_count"] == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT strength FROM relations WHERE relation_id = 'rel_quiet'").fetchone()
    conn.close()
    assert row[0] < 0.8


def test_drift_positive_events_increase_strength(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_with_events(
        db_path,
        "rel_happy",
        strength=0.5,
        summaries_with_offsets=[
            ("一起开心吃饭", 1),
            ("顺利完成项目", 3),
            ("互相关心", 5),
        ],
    )

    result = drift_relations(db_path, window_days=30)
    assert result["drifted_count"] == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT strength FROM relations WHERE relation_id = 'rel_happy'").fetchone()
    conn.close()
    assert row[0] > 0.5


def test_drift_negative_events_decrease_strength(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_with_events(
        db_path,
        "rel_bad",
        strength=0.7,
        summaries_with_offsets=[
            ("发生争执冲突", 2),
            ("糟糕的会议", 4),
        ],
    )

    result = drift_relations(db_path, window_days=30)
    assert result["drifted_count"] == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT strength FROM relations WHERE relation_id = 'rel_bad'").fetchone()
    conn.close()
    assert row[0] < 0.7


def test_drift_clamps_to_ceiling(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_with_events(
        db_path,
        "rel_max",
        strength=0.99,
        summaries_with_offsets=[("顺利完成", 1)],
    )
    drift_relations(db_path, window_days=30)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT strength FROM relations WHERE relation_id = 'rel_max'").fetchone()
    conn.close()
    assert row[0] <= 1.0


def test_drift_records_patch(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_with_events(db_path, "rel_patched", strength=0.6, summaries_with_offsets=[])

    drift_relations(db_path, window_days=30)

    conn = sqlite3.connect(db_path)
    patch_count = conn.execute(
        "SELECT COUNT(*) FROM patches WHERE operation = 'update_entity' AND target_id = 'rel_patched'",
    ).fetchone()[0]
    conn.close()
    assert patch_count == 1
