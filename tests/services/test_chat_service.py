import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.llm.providers.mock import MockLLMClient
from we_together.services.chat_service import run_turn, get_adapter, ADAPTERS
from we_together.services.scene_service import create_scene, add_scene_participant


def test_get_adapter_returns_known():
    assert get_adapter("claude").name == "claude"
    assert get_adapter("openai").name == "openai_compat"
    assert get_adapter("openai_compat").name == "openai_compat"


def test_run_turn_returns_request_response_and_updates_graph(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="repl test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )

    mock = MockLLMClient(scripted_responses=["我在听"])
    result = run_turn(
        db_path=db_path,
        scene_id=scene_id,
        user_input="在吗",
        llm_client=mock,
        adapter_name="claude",
    )

    assert result["response"]["text"] == "我在听"
    assert result["event_id"].startswith("evt_")
    assert result["applied_patch_count"] >= 1

    conn = sqlite3.connect(db_path)
    ev = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_id = ?", (result["event_id"],),
    ).fetchone()[0]
    state_count = conn.execute(
        "SELECT COUNT(*) FROM states WHERE scope_type = 'scene' AND scope_id = ?", (scene_id,),
    ).fetchone()[0]
    conn.close()

    assert ev == 1
    assert state_count >= 1


def test_run_turn_with_openai_adapter(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    scene_id = create_scene(
        db_path=db_path,
        scene_type="private_chat",
        scene_summary="repl openai test",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(
        db_path=db_path, scene_id=scene_id, person_id="person_x",
        activation_state="explicit", activation_score=1.0, is_speaking=True,
    )

    mock = MockLLMClient(scripted_responses=["ok"])
    result = run_turn(
        db_path=db_path,
        scene_id=scene_id,
        user_input="一起走吗",
        llm_client=mock,
        adapter_name="openai",
    )
    assert result["response"]["raw"]["adapter"] == "openai_compat"
