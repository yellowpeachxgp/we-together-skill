from datetime import UTC, datetime, timedelta
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.services.relation_conflict_service import detect_relation_conflicts


def _seed_relation_events(
    db_path,
    relation_id: str,
    summaries_with_offsets: list[tuple[str, float]],
    *,
    participants: list[str] | None = None,
):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO relations(
            relation_id, core_type, custom_label, summary, directionality,
            strength, stability, visibility, status, confidence, metadata_json,
            created_at, updated_at
        ) VALUES(?, 'friendship', '朋友', '', 'bidirectional',
                 0.5, 0.5, 'known', 'active', 0.7, '{}', datetime('now'), datetime('now'))
        """,
        (relation_id,),
    )
    # persons
    participants = participants or []
    for pid in participants:
        conn.execute(
            """
            INSERT OR IGNORE INTO persons(
                person_id, primary_name, status, confidence, metadata_json,
                created_at, updated_at
            ) VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
            """,
            (pid, pid),
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
            "INSERT INTO event_targets(event_id, target_type, target_id, impact_hint) "
            "VALUES(?, 'relation', ?, 'test')",
            (eid, relation_id),
        )
        for pid in participants:
            conn.execute(
                "INSERT INTO event_participants(event_id, person_id, participant_role) "
                "VALUES(?, ?, 'speaker')",
                (eid, pid),
            )
    conn.commit()
    conn.close()


def test_detect_no_conflict_for_uniform_positive(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_events(db_path, "rel_calm", [
        ("一起开心", 4),
        ("互相关心", 3),
        ("顺利完成", 1),
    ])

    result = detect_relation_conflicts(db_path)
    assert result["conflict_count"] == 0


def test_detect_conflict_when_sentiment_oscillates(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_events(
        db_path,
        "rel_turbulent",
        [
            ("一起开心吃饭", 8),      # +
            ("冲突争执", 6),           # -
            ("互相关心和解", 4),       # +
            ("烦糟糕", 2),             # -
        ],
        participants=["p_a", "p_b"],
    )

    result = detect_relation_conflicts(db_path, min_reversals=2)
    assert result["conflict_count"] == 1
    d = result["details"][0]
    assert d["relation_id"] == "rel_turbulent"
    assert d["reversals"] >= 2
    assert d["positive_count"] >= 2
    assert d["negative_count"] >= 2
    assert set(d["participants"]) == {"p_a", "p_b"}


def test_detect_conflict_emits_memory(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_events(
        db_path,
        "rel_fighting",
        [
            ("一起开心", 8),
            ("冲突争执", 6),
            ("互相关心", 4),
            ("烦糟糕", 2),
        ],
        participants=["p_x", "p_y"],
    )

    result = detect_relation_conflicts(
        db_path,
        min_reversals=2,
        emit_memory=True,
        source_event_id="evt_rel_fighting_3",
    )
    assert result["conflict_count"] == 1

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT memory_id, memory_type, summary FROM memories WHERE memory_type='conflict_signal'"
    ).fetchall()
    assert len(rows) == 1
    mem_id = rows[0][0]
    owners = conn.execute(
        "SELECT owner_id FROM memory_owners WHERE memory_id = ?",
        (mem_id,),
    ).fetchall()
    assert {r[0] for r in owners} == {"p_x", "p_y"}
    conn.close()


def test_single_reversal_does_not_trigger(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _seed_relation_events(db_path, "rel_minor", [
        ("一起开心", 5),    # +
        ("冲突争执", 2),    # -
    ])

    result = detect_relation_conflicts(db_path, min_reversals=2)
    assert result["conflict_count"] == 0
