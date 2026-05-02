import json
import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.runtime.sqlite_retrieval import (
    build_runtime_retrieval_package_from_db,
    _compute_memory_score,
    _memory_recency_factor,
)
from we_together.services.scene_service import create_scene, add_scene_participant


def _seed_memory(db_path, memory_id, memory_type, owner_ids, confidence=0.7,
                 relevance=0.8, created_at_iso=None, is_shared=1, metadata=None):
    conn = sqlite3.connect(db_path)
    created_at = created_at_iso or "datetime('now')"
    if created_at_iso:
        conn.execute(
            """
            INSERT INTO memories(
                memory_id, memory_type, summary, relevance_score, confidence,
                is_shared, status, metadata_json, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (memory_id, memory_type, f"memo {memory_id}", relevance, confidence,
             is_shared, json.dumps(metadata or {}), created_at_iso, created_at_iso),
        )
    else:
        conn.execute(
            """
            INSERT INTO memories(
                memory_id, memory_type, summary, relevance_score, confidence,
                is_shared, status, metadata_json, created_at, updated_at
            ) VALUES(?, ?, ?, ?, ?, ?, 'active', ?, datetime('now'), datetime('now'))
            """,
            (memory_id, memory_type, f"memo {memory_id}", relevance, confidence,
             is_shared, json.dumps(metadata or {})),
        )
    for oid in owner_ids:
        conn.execute(
            "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) VALUES(?, 'person', ?, NULL)",
            (memory_id, oid),
        )
    conn.commit()
    conn.close()


def _add_person(db_path, person_id, name):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json,
                            created_at, updated_at)
        VALUES(?, ?, 'active', 0.8, '{}', datetime('now'), datetime('now'))
        """,
        (person_id, name),
    )
    conn.commit()
    conn.close()


def test_memory_recency_factor_zero_days():
    # 今天刚创建的记忆应接近 1.0
    from datetime import UTC, datetime
    now_iso = datetime.now(UTC).isoformat()
    assert _memory_recency_factor(now_iso) > 0.95


def test_memory_recency_factor_half_life():
    # 正好半衰期 60 天 → ~0.5
    from datetime import UTC, datetime, timedelta
    past = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    factor = _memory_recency_factor(past)
    assert 0.4 <= factor <= 0.6


def test_scene_match_boosts_score(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_s", "S")

    _seed_memory(db_path, "mem_work", "shared_memory", ["person_s"],
                 metadata={"scene_type": "work_discussion"})
    _seed_memory(db_path, "mem_life", "shared_memory", ["person_s"],
                 metadata={"scene_type": "private_chat"})

    scene_id = create_scene(
        db_path=db_path, scene_type="work_discussion", scene_summary="work",
        environment={"location_scope": "remote", "channel_scope": "group_channel",
                     "visibility_scope": "group_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id="person_s",
                           activation_state="explicit", activation_score=1.0, is_speaking=True)

    pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    mems = {m["memory_id"]: m for m in pkg["relevant_memories"]}
    assert mems["mem_work"]["composite_score"] > mems["mem_life"]["composite_score"]


def test_memory_score_includes_composite_field(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_cs", "CS")
    _seed_memory(db_path, "mem_cs", "shared_memory", ["person_cs"])

    scene_id = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="x",
        environment={"location_scope": "remote", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id="person_cs",
                           activation_state="explicit", activation_score=1.0, is_speaking=True)

    pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    assert len(pkg["relevant_memories"]) == 1
    assert "composite_score" in pkg["relevant_memories"][0]
    assert pkg["relevant_memories"][0]["composite_score"] > 0


def test_memory_score_breakdown_when_debug(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_db", "DB")
    _seed_memory(db_path, "mem_db", "shared_memory", ["person_db"],
                 metadata={"scene_type": "work_discussion"})

    scene_id = create_scene(
        db_path=db_path, scene_type="work_discussion", scene_summary="w",
        environment={"location_scope": "remote", "channel_scope": "group_channel",
                     "visibility_scope": "group_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=scene_id, person_id="person_db",
                          activation_state="explicit", activation_score=1.0, is_speaking=True)

    # 默认不带 breakdown
    pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
    assert "score_breakdown" not in pkg["relevant_memories"][0]

    # debug_scores=True 时带 breakdown
    pkg_dbg = build_runtime_retrieval_package_from_db(
        db_path=db_path, scene_id=scene_id, debug_scores=True,
    )
    mem = pkg_dbg["relevant_memories"][0]
    assert "score_breakdown" in mem
    bd = mem["score_breakdown"]
    for key in ("base_type", "relevance", "confidence", "recency",
                "overlap_factor", "scene_factor", "composite"):
        assert key in bd, f"missing key {key}"
    # composite 应与顶层 composite_score 一致
    assert abs(bd["composite"] - mem["composite_score"]) < 1e-9
    # scene_type 匹配 → scene_factor > 1
    assert bd["scene_factor"] > 1.0
