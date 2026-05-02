import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.runtime.sqlite_retrieval import (  # noqa: E402
    build_runtime_retrieval_package_from_db,
)


def _seed_high_confidence_event(db_path, scene_id, summary, confidence=0.85, actors=None):
    c = sqlite3.connect(db_path)
    eid = f"evt_echo_{summary[:6]}"
    c.execute(
        """INSERT INTO events(event_id, event_type, source_type, scene_id, timestamp,
           summary, visibility_level, confidence, is_structured,
           raw_evidence_refs_json, metadata_json, created_at) VALUES(?,
           'dialogue_event', 'test', ?, datetime('now'), ?, 'visible', ?, 1, '[]',
           '{}', datetime('now'))""",
        (eid, scene_id, summary, confidence),
    )
    for a in actors or []:
        c.execute(
            "INSERT INTO event_participants(event_id, person_id, participant_role) "
            "VALUES(?, ?, 'actor')",
            (eid, a),
        )
    c.commit()
    c.close()


def test_cross_scene_echoes_surfaced(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    work_scene = summary["scenes"]["work"]
    date_scene = summary["scenes"]["date"]

    # 在 work 场景插高权重 event
    _seed_high_confidence_event(db_path, work_scene, "important work decision", 0.9)

    pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=date_scene)
    echoes = pkg.get("cross_scene_echoes", [])
    scene_ids = {e["scene_id"] for e in echoes}
    assert work_scene in scene_ids


def test_cross_scene_echoes_skip_current_scene(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    work_scene = summary["scenes"]["work"]

    _seed_high_confidence_event(db_path, work_scene, "my own", 0.9)

    pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=work_scene)
    for e in pkg.get("cross_scene_echoes", []):
        assert e["scene_id"] != work_scene


def test_cross_scene_echoes_respect_confidence_floor(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    work_scene = summary["scenes"]["work"]
    date_scene = summary["scenes"]["date"]

    _seed_high_confidence_event(db_path, work_scene, "low conf", confidence=0.2)

    pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=date_scene)
    for e in pkg.get("cross_scene_echoes", []):
        assert e["confidence"] >= 0.7
