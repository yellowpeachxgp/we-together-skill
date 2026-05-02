import sqlite3
import sys
from pathlib import Path

# 把 scripts 加入 path 以便 import seed_demo
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from seed_demo import seed_society_c  # noqa: E402

from we_together.runtime.sqlite_retrieval import build_runtime_retrieval_package_from_db


def test_seed_society_c_creates_expected_entities(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"

    conn = sqlite3.connect(db_path)
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    relation_count = conn.execute("SELECT COUNT(*) FROM relations WHERE status = 'active'").fetchone()[0]
    scene_count = conn.execute("SELECT COUNT(*) FROM scenes").fetchone()[0]
    memory_count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
    group_count = conn.execute("SELECT COUNT(*) FROM groups").fetchone()[0]
    conn.close()

    assert person_count == 8
    assert relation_count >= 5
    assert scene_count == 3
    assert memory_count >= 3
    assert group_count == 1
    assert summary["persons"]["alice"].startswith("person_")


def test_seed_idempotent_on_second_run(temp_project_dir):
    s1 = seed_society_c(temp_project_dir)
    s2 = seed_society_c(temp_project_dir)
    assert s1["persons"] == s2["persons"]

    db_path = temp_project_dir / "db" / "main.sqlite3"
    conn = sqlite3.connect(db_path)
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    conn.close()
    assert person_count == 8


def test_seed_produces_usable_retrieval_for_each_scene(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"

    for scene_key, scene_id in summary["scenes"].items():
        pkg = build_runtime_retrieval_package_from_db(db_path=db_path, scene_id=scene_id)
        assert pkg["scene_summary"]["scene_id"] == scene_id
        assert len(pkg["participants"]) >= 1
        assert "response_policy" in pkg
