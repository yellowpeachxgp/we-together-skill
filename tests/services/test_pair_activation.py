import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from seed_demo import seed_society_c  # noqa: E402

from we_together.llm.providers.mock import MockLLMClient  # noqa: E402
from we_together.services.self_activation_service import (  # noqa: E402
    self_activate_pair_interactions,
)


def test_pair_activation_creates_latent_interaction_event(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    llm = MockLLMClient(scripted_json=[{"summary": "他们聊起了项目进度"}])
    result = self_activate_pair_interactions(
        db_path=db_path, scene_id=scene_id, llm_client=llm, per_run_limit=1,
    )

    assert result["created_count"] == 1
    eid = result["event_ids"][0]
    c = sqlite3.connect(db_path)
    ev = c.execute(
        "SELECT event_type, summary FROM events WHERE event_id = ?", (eid,),
    ).fetchone()
    assert ev[0] == "latent_interaction_event"
    assert ev[1] == "他们聊起了项目进度"
    parts = c.execute(
        "SELECT person_id FROM event_participants WHERE event_id = ?", (eid,),
    ).fetchall()
    assert len(parts) == 2
    c.close()


def test_pair_activation_budget_exhausted(temp_project_dir):
    summary = seed_society_c(temp_project_dir)
    db_path = temp_project_dir / "db" / "main.sqlite3"
    scene_id = summary["scenes"]["work"]

    # 预先占满预算
    llm = MockLLMClient(default_json={"summary": "x"})
    for _ in range(2):
        self_activate_pair_interactions(
            db_path=db_path, scene_id=scene_id, llm_client=llm,
            daily_budget=2, per_run_limit=1,
        )
    # 第 3 次应返回 budget_exhausted
    result = self_activate_pair_interactions(
        db_path=db_path, scene_id=scene_id, llm_client=llm,
        daily_budget=2, per_run_limit=1,
    )
    assert result["reason"] == "daily_budget_exhausted"
