import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.db.bootstrap import bootstrap_project  # noqa: E402
from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.runtime.sqlite_retrieval import (  # noqa: E402
    build_runtime_retrieval_package_from_db,
)
from we_together.services.memory_recall_service import (  # noqa: E402
    recall_anniversary_memories,
)
from we_together.simulation.what_if_service import simulate_what_if  # noqa: E402


# --- as_of retrieval ---

def test_as_of_retrieval_filters_recent_changes(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    # 插入一条早期 patch 和一条近期 patch
    c = sqlite3.connect(db)
    for pid, applied in [("p_early", "2020-01-01T00:00:00+00:00"),
                          ("p_late", "2030-12-31T23:59:59+00:00")]:
        c.execute(
            """INSERT INTO patches(patch_id, source_event_id, target_type, target_id,
               operation, payload_json, confidence, reason, status, applied_at,
               created_at) VALUES(?, 'src', 'person', 'x', 'update_entity', '{}',
               0.5, 'r', 'applied', ?, datetime('now'))""",
            (pid, applied),
        )
    c.commit(); c.close()

    pkg_now = build_runtime_retrieval_package_from_db(db_path=db, scene_id=scene_id)
    ids_now = {p["patch_id"] for p in pkg_now["recent_changes"]}
    assert "p_late" in ids_now

    pkg_2020 = build_runtime_retrieval_package_from_db(
        db_path=db, scene_id=scene_id, as_of="2021-01-01T00:00:00+00:00",
    )
    ids_2020 = {p["patch_id"] for p in pkg_2020["recent_changes"]}
    assert "p_early" in ids_2020
    assert "p_late" not in ids_2020


def test_as_of_bypasses_cache(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    # 先写入缓存
    build_runtime_retrieval_package_from_db(
        db_path=db, scene_id=scene_id, input_hash="warm",
    )
    # as_of 请求应忽略缓存
    pkg = build_runtime_retrieval_package_from_db(
        db_path=db, scene_id=scene_id, input_hash="warm", as_of="2021-01-01T00:00:00+00:00",
    )
    assert "recent_changes" in pkg


# --- memory_recall ---

def test_memory_recall_triggers_on_anniversary(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    # 一条 30 天前的高 relevance memory
    c = sqlite3.connect(db)
    ts = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    c.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_anniv','shared_memory','重要回忆',0.9,0.8,1,'active','{}',?,?)""",
        (ts, ts),
    )
    c.commit(); c.close()

    result = recall_anniversary_memories(db, daily_budget=2)
    assert result["recalled_count"] == 1
    assert result["events"][0]["memory_id"] == "m_anniv"
    assert result["events"][0]["age_days"] == 30


def test_memory_recall_budget_exhausted(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    c = sqlite3.connect(db)
    ts = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    c.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_rec','shared_memory','x',0.9,0.8,1,'active','{}',?,?)""",
        (ts, ts),
    )
    c.commit(); c.close()

    recall_anniversary_memories(db, daily_budget=1)
    r2 = recall_anniversary_memories(db, daily_budget=1)
    assert r2["reason"] == "daily_budget_exhausted"


# --- what-if ---

def test_what_if_returns_predictions(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    llm = MockLLMClient(scripted_json=[{
        "predictions": [
            {"horizon_days": 7, "prediction": "冲突爆发", "affected_entities": ["Alice"]},
            {"horizon_days": 30, "prediction": "关系重组", "affected_entities": ["Bob"]},
        ],
        "confidence": 0.7,
    }])
    result = simulate_what_if(db_path=db, scene_id=scene_id,
                               hypothesis="Alice 离职", llm_client=llm)
    assert result["hypothesis"] == "Alice 离职"
    assert len(result["predictions"]) == 2
    assert result["confidence"] == 0.7
