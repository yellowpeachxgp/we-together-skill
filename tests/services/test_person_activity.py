import sqlite3
import sys
from pathlib import Path

# 导入 seed_demo 工具
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.services.person_activity_service import build_person_activity


def test_person_activity_view_returns_all_sections(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"

    alice_id = summary["persons"]["alice"]
    view = build_person_activity(db_path, alice_id, event_limit=20)

    assert view["person"]["primary_name"] == "Alice"
    assert len(view["active_relations"]) >= 1
    assert len(view["memories"]) >= 1
    assert len(view["scenes"]) >= 1


def test_person_activity_raises_for_missing(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    import pytest
    with pytest.raises(ValueError):
        build_person_activity(db_path, "person_nope")
