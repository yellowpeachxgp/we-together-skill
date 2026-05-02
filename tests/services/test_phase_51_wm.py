"""Phase 51 — 世界建模升维 (WM slices)。"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _seed_person(db: Path, pid: str = "p_world_1") -> str:
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "INSERT INTO persons(person_id, primary_name, status, confidence, "
            "metadata_json, created_at, updated_at) VALUES(?, 'Alice', 'active', 0.9, "
            "'{}', datetime('now'), datetime('now'))",
            (pid,),
        )
        conn.commit()
    finally:
        conn.close()
    return pid


def test_migration_0018_0019_0020_installed(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    names = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "objects" in names
    assert "object_ownership_history" in names
    assert "places" in names
    assert "projects" in names


def test_register_object_creates_entity_link(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import register_object
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pid = _seed_person(db)
    r = register_object(db, kind="possession", name="笔记本电脑",
                         owner_type="person", owner_id=pid)
    assert r["object_id"].startswith("obj_")

    conn = sqlite3.connect(db)
    link_count = conn.execute(
        "SELECT COUNT(*) FROM entity_links WHERE from_type='person' "
        "AND from_id=? AND relation_type='owns' AND to_type='object' "
        "AND to_id=?", (pid, r["object_id"]),
    ).fetchone()[0]
    conn.close()
    assert link_count == 1


def test_transfer_object_updates_ownership_and_history(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import register_object, transfer_object
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    p_alice = _seed_person(db, "p_alice_1")
    p_bob = _seed_person(db, "p_bob_1")

    r = register_object(db, kind="gift", name="书",
                         owner_type="person", owner_id=p_alice)
    oid = r["object_id"]

    t = transfer_object(db, object_id=oid,
                         new_owner_type="person", new_owner_id=p_bob)
    assert t["to"]["id"] == p_bob

    conn = sqlite3.connect(db)
    # 旧 link 被删
    link_alice = conn.execute(
        "SELECT COUNT(*) FROM entity_links WHERE from_id=? AND to_id=? "
        "AND relation_type='owns'", (p_alice, oid),
    ).fetchone()[0]
    link_bob = conn.execute(
        "SELECT COUNT(*) FROM entity_links WHERE from_id=? AND to_id=? "
        "AND relation_type='owns'", (p_bob, oid),
    ).fetchone()[0]
    # 历史记录
    hist = conn.execute(
        "SELECT COUNT(*) FROM object_ownership_history WHERE object_id=?",
        (oid,),
    ).fetchone()[0]
    conn.close()
    assert link_alice == 0
    assert link_bob == 1
    assert hist == 1


def test_register_place_and_lineage(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import register_place, get_place_lineage
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    city = register_place(db, name="北京", scope="city")
    venue = register_place(db, name="中关村", scope="district",
                            parent_place_id=city["place_id"])
    room = register_place(db, name="会议室 A",
                           scope="room", parent_place_id=venue["place_id"])

    lineage = get_place_lineage(db, room["place_id"])
    names = [p["name"] for p in lineage]
    assert names == ["北京", "中关村", "会议室 A"]


def test_register_project_with_participants(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import (
        register_project, list_projects_for_person,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pa = _seed_person(db, "p_proj_1")
    pb = _seed_person(db, "p_proj_2")

    r = register_project(db, name="v0.17 发布", goal="发布 we-together v0.17",
                          participants=[pa, pb])
    assert r["project_id"].startswith("proj_")

    pa_projects = list_projects_for_person(db, pa)
    assert len(pa_projects) == 1
    assert pa_projects[0]["name"] == "v0.17 发布"


def test_set_project_status_sets_ended_at(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import register_project, set_project_status
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    r = register_project(db, name="temp")
    set_project_status(db, r["project_id"], "completed")

    conn = sqlite3.connect(db)
    row = conn.execute(
        "SELECT status, ended_at FROM projects WHERE project_id=?",
        (r["project_id"],),
    ).fetchone()
    conn.close()
    assert row[0] == "completed"
    assert row[1] is not None


def test_set_project_status_invalid_raises(temp_project_with_migrations):
    import pytest
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import register_project, set_project_status
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    r = register_project(db, name="x")
    with pytest.raises(ValueError, match="invalid status"):
        set_project_status(db, r["project_id"], "bogus")


def test_list_objects_by_owner(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import (
        register_object, list_objects_by_owner,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pid = _seed_person(db, "p_o_list")
    register_object(db, kind="tool", name="笔",
                     owner_type="person", owner_id=pid)
    register_object(db, kind="tool", name="纸",
                     owner_type="person", owner_id=pid)
    items = list_objects_by_owner(db, "person", pid)
    assert len(items) == 2


def test_link_event_to_place(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import register_place, link_event_to_place
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pl = register_place(db, name="办公室", scope="venue")

    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO events(event_id, event_type, source_type, timestamp, summary,
           visibility_level, confidence, is_structured, raw_evidence_refs_json,
           metadata_json, created_at) VALUES('e_place_1', 'narration', 'test',
           datetime('now'), 'x', 'visible', 0.7, 1, '[]', '{}',
           datetime('now'))"""
    )
    conn.commit()
    conn.close()

    link_event_to_place(db, "e_place_1", pl["place_id"])

    conn = sqlite3.connect(db)
    cnt = conn.execute(
        "SELECT COUNT(*) FROM entity_links WHERE from_type='event' AND from_id='e_place_1' "
        "AND relation_type='at' AND to_type='place'"
    ).fetchone()[0]
    conn.close()
    assert cnt == 1


def test_active_world_for_scene(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import (
        register_object, register_place, register_project, link_event_to_place,
        active_world_for_scene,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pa = _seed_person(db, "p_aw_1")
    pb = _seed_person(db, "p_aw_2")

    # scene + participants
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO scenes(scene_id, scene_type, status, created_at, updated_at) "
        "VALUES('s_aw', 'work', 'active', datetime('now'), datetime('now'))"
    )
    for p in (pa, pb):
        conn.execute(
            "INSERT INTO scene_participants(scene_id, person_id, activation_score, "
            "activation_state, is_speaking, reason_json, created_at, updated_at) "
            "VALUES('s_aw', ?, 0.7, 'explicit', 0, '{}', datetime('now'), datetime('now'))",
            (p,),
        )
    conn.execute(
        """INSERT INTO events(event_id, event_type, source_type, timestamp, scene_id,
           summary, visibility_level, confidence, is_structured,
           raw_evidence_refs_json, metadata_json, created_at)
           VALUES('e_aw', 'narration', 'test', datetime('now'), 's_aw', 'x', 'visible',
           0.7, 1, '[]', '{}', datetime('now'))"""
    )
    conn.commit()
    conn.close()

    register_object(db, kind="tool", name="笔",
                     owner_type="person", owner_id=pa)
    pl = register_place(db, name="会议室")
    link_event_to_place(db, "e_aw", pl["place_id"])
    register_project(db, name="季度汇报",
                      participants=[pa, pb])

    world = active_world_for_scene(db, "s_aw")
    assert len(world["participants"]) == 2
    assert len(world["objects"]) >= 1
    assert len(world["places"]) >= 1
    assert len(world["projects"]) >= 1


def test_world_objects_have_time_range(temp_project_with_migrations):
    """不变式 #26: 所有世界对象必须有 effective_from"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.world_service import (
        register_object, register_place, register_project,
    )
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    pid = _seed_person(db, "p_time")

    r_obj = register_object(db, kind="tool", owner_type="person", owner_id=pid)
    r_place = register_place(db, name="家")
    r_proj = register_project(db, name="side project")

    conn = sqlite3.connect(db)
    o_eff = conn.execute(
        "SELECT effective_from FROM objects WHERE object_id=?",
        (r_obj["object_id"],),
    ).fetchone()[0]
    p_eff = conn.execute(
        "SELECT effective_from FROM places WHERE place_id=?",
        (r_place["place_id"],),
    ).fetchone()[0]
    proj_started = conn.execute(
        "SELECT started_at FROM projects WHERE project_id=?",
        (r_proj["project_id"],),
    ).fetchone()[0]
    conn.close()

    assert o_eff is not None
    assert p_eff is not None
    assert proj_started is not None


def test_world_cli_script_importable():
    import importlib.util
    p = REPO_ROOT / "scripts" / "world_cli.py"
    spec = importlib.util.spec_from_file_location("world_cli_t", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert callable(mod.main)
