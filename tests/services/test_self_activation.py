import sqlite3

from we_together.db.bootstrap import bootstrap_project
from we_together.llm.providers.mock import MockLLMClient
from we_together.services.scene_service import add_scene_participant, create_scene
from we_together.services.self_activation_service import self_activate


def _add_person(db_path, pid, name, persona=None):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO persons(person_id, primary_name, status, persona_summary,
                            confidence, metadata_json, created_at, updated_at)
        VALUES(?, ?, 'active', ?, 0.8, '{}', datetime('now'), datetime('now'))
        """,
        (pid, name, persona),
    )
    conn.commit()
    conn.close()


def test_self_activate_creates_reflection_events_stub(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_sa1", "Alice", "理性")
    _add_person(db_path, "person_sa2", "Bob", "直接")

    sid = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="夜间沉思",
        environment={"location_scope": "remote", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_sa1",
                          activation_state="explicit", activation_score=1.0, is_speaking=True)
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_sa2",
                          activation_state="latent", activation_score=0.7, is_speaking=False)

    result = self_activate(db_path=db_path, scene_id=sid, daily_budget=3, per_run_limit=2)
    assert result["created_count"] == 2

    conn = sqlite3.connect(db_path)
    ev_count = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_type = 'self_reflection_event'"
    ).fetchone()[0]
    conn.close()
    assert ev_count == 2


def test_self_activate_with_llm(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_sa_llm", "Cara", "爱读书")

    sid = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="深夜独处",
        environment={"location_scope": "home", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_sa_llm",
                          activation_state="explicit", activation_score=1.0, is_speaking=True)

    mock = MockLLMClient(scripted_responses=["想到小时候的一本书。"])
    result = self_activate(db_path=db_path, scene_id=sid, llm_client=mock, per_run_limit=1)
    assert result["created_count"] == 1

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT summary FROM events WHERE event_type = 'self_reflection_event'"
    ).fetchone()
    conn.close()
    assert row[0] == "想到小时候的一本书。"


def test_self_activate_respects_daily_budget(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_sab", "Dan")
    sid = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="budget",
        environment={"location_scope": "remote", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_sab",
                          activation_state="explicit", activation_score=1.0, is_speaking=True)

    # 第一次：允许 1 条
    r1 = self_activate(db_path=db_path, scene_id=sid, daily_budget=1, per_run_limit=1)
    assert r1["created_count"] == 1

    # 第二次：预算用尽
    r2 = self_activate(db_path=db_path, scene_id=sid, daily_budget=1, per_run_limit=1)
    assert r2["created_count"] == 0
    assert r2["reason"] == "daily_budget_exhausted"


def test_self_activate_derives_individual_memory(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_zm", "Zm")
    sid = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="derive memo",
        environment={"location_scope": "remote", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_zm",
                          activation_state="explicit", activation_score=1.0, is_speaking=True)

    r = self_activate(db_path=db_path, scene_id=sid,
                       daily_budget=1, per_run_limit=1, derive_memories=True)
    assert r["created_count"] == 1

    conn = sqlite3.connect(db_path)
    mem_count = conn.execute(
        "SELECT COUNT(*) FROM memories WHERE memory_type = 'individual_memory'"
    ).fetchone()[0]
    owner_count = conn.execute(
        "SELECT COUNT(*) FROM memory_owners WHERE owner_id = 'person_zm' AND role_label = 'self'"
    ).fetchone()[0]
    conn.close()
    assert mem_count >= 1
    assert owner_count >= 1


def test_self_activate_can_skip_memory_derivation(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    _add_person(db_path, "person_zm2", "Zm2")
    sid = create_scene(
        db_path=db_path, scene_type="private_chat", scene_summary="no memo",
        environment={"location_scope": "remote", "channel_scope": "private_dm",
                     "visibility_scope": "mutual_visible"},
    )
    add_scene_participant(db_path=db_path, scene_id=sid, person_id="person_zm2",
                          activation_state="explicit", activation_score=1.0, is_speaking=True)

    self_activate(db_path=db_path, scene_id=sid, derive_memories=False, per_run_limit=1)

    conn = sqlite3.connect(db_path)
    mem = conn.execute(
        "SELECT COUNT(*) FROM memories WHERE memory_type = 'individual_memory'"
    ).fetchone()[0]
    conn.close()
    assert mem == 0
