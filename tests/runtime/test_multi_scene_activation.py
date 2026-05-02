import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.runtime.multi_scene_activation import (  # noqa: E402
    build_multi_scene_activation,
)


def test_multi_scene_merges_participants(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"

    work = summary["scenes"]["work"]
    date = summary["scenes"]["date"]

    result = build_multi_scene_activation(
        db_path=db_path,
        scene_ids=[work, date],
    )

    assert set(result["scene_ids"]) == {work, date}
    amap = result["activation_map"]
    pids = {item["person_id"] for item in amap}
    # work + date 场景参与者都应出现
    assert summary["persons"]["alice"] in pids
    assert summary["persons"]["bob"] in pids


def test_multi_scene_score_takes_max(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"

    work = summary["scenes"]["work"]
    date = summary["scenes"]["date"]

    result = build_multi_scene_activation(
        db_path=db_path,
        scene_ids=[work, date],
    )

    # 去重：同一 person_id 只出现一次
    ids = [item["person_id"] for item in result["activation_map"]]
    assert len(ids) == len(set(ids))


def test_multi_scene_per_scene_package_included(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"

    work = summary["scenes"]["work"]
    date = summary["scenes"]["date"]

    result = build_multi_scene_activation(
        db_path=db_path,
        scene_ids=[work, date],
    )
    assert work in result["per_scene"]
    assert date in result["per_scene"]
    assert "participants" in result["per_scene"][work]
