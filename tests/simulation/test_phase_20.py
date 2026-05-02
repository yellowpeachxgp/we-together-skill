import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.services.retire_person_service import retire_person  # noqa: E402
from we_together.simulation.conflict_predictor import predict_conflicts  # noqa: E402
from we_together.simulation.era_evolution import simulate_era  # noqa: E402
from we_together.simulation.scene_scripter import write_scene_script  # noqa: E402


def test_conflict_predictor_no_conflict(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    r = predict_conflicts(db, llm_client=MockLLMClient())
    # society_c 无真实冲突信号
    assert r["prediction_count"] == 0


def test_conflict_predictor_with_scripted(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # 人工插 relation + 反转 events
    c = sqlite3.connect(db)
    c.execute("""INSERT INTO relations(relation_id, core_type, custom_label, summary,
                 directionality, strength, stability, visibility, status, confidence,
                 metadata_json, created_at, updated_at) VALUES('rel_cf','friendship','',
                 '','bidirectional',0.5,0.5,'known','active',0.7,'{}',
                 datetime('now'),datetime('now'))""")
    for i, s in enumerate(["一起开心", "冲突争执", "互相关心", "烦糟糕"]):
        eid = f"evt_cf_{i}"
        c.execute("""INSERT INTO events(event_id, event_type, source_type, timestamp,
                     summary, visibility_level, confidence, is_structured,
                     raw_evidence_refs_json, metadata_json, created_at) VALUES(?,
                     'dialogue_event', 'm', datetime('now', '-'||?||' days'), ?,
                     'visible', 0.8, 0, '[]', '{}', datetime('now'))""",
                   (eid, (4 - i) * 2, s))
        c.execute("INSERT INTO event_targets(event_id, target_type, target_id, impact_hint) "
                   "VALUES(?, 'relation', 'rel_cf', 'test')", (eid,))
    c.commit(); c.close()

    llm = MockLLMClient(scripted_json=[{
        "predictions": [
            {"relation_id": "rel_cf", "horizon_days": 7,
             "probability": 0.7, "reason": "高反转"},
        ]
    }])
    r = predict_conflicts(db, window_days=30, llm_client=llm)
    assert r["prediction_count"] == 1


def test_scene_scripter_produces_script(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    llm = MockLLMClient(scripted_json=[{
        "script": [
            {"speaker": "Alice", "text": "今天开始做架构"},
            {"speaker": "Bob", "text": "好的，我写后端"},
            {"speaker": "Alice", "text": "下周 review"},
        ]
    }])
    r = write_scene_script(db, scene_id=scene_id, turns=3, llm_client=llm)
    assert r["turn_count"] == 3
    assert r["script"][0]["speaker"] == "Alice"


def test_retire_person(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    alice = summary["persons"]["alice"]

    r = retire_person(db, alice)
    assert r["person_id"] == alice
    # 再次调用 → already_retired
    r2 = retire_person(db, alice)
    assert r2.get("already_retired") is True

    c = sqlite3.connect(db)
    status = c.execute("SELECT status FROM persons WHERE person_id = ?",
                         (alice,)).fetchone()[0]
    c.close()
    assert status == "retired"


def test_retire_unknown_person(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    import pytest
    with pytest.raises(ValueError):
        retire_person(db, "person_nonexistent")


def test_era_simulation_runs(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db = temp_project_dir / "db" / "main.sqlite3"
    r = simulate_era(db, days=2, pair_budget_per_day=1)
    assert r["days"] == 2
    assert len(r["daily_reports"]) == 2
    assert "pair_events" in r["daily_reports"][0]
