"""Phase 42 — 联邦 MVP (FD slices)。"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_server_module():
    p = REPO_ROOT / "scripts" / "federation_http_server.py"
    spec = importlib.util.spec_from_file_location("fed_http_t", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_capabilities_contains_protocol_version():
    m = _load_server_module()
    cap = m._capabilities()
    assert cap["federation_protocol_version"] in ("1", "1.1")
    assert cap["skill_schema_version"] == "1"
    assert cap["read_only"] is True


def test_list_persons(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pF','Alice Fed','active',0.9,"
        "'{}', datetime('now'),datetime('now'))"
    )
    conn.commit()
    conn.close()

    m = _load_server_module()
    r = m._list_persons(db, limit=10)
    assert r["count"] >= 1
    names = {p["primary_name"] for p in r["persons"]}
    assert "Alice Fed" in names


def test_get_person_existing_and_missing(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    import json as _json

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pG','Gamma','active',0.7,?,"
        "datetime('now'),datetime('now'))",
        (_json.dumps({"note": "hello"}),),
    )
    conn.commit()
    conn.close()

    m = _load_server_module()
    p = m._get_person(db, "pG")
    assert p is not None
    assert p["primary_name"] == "Gamma"
    assert p["metadata"]["note"] == "hello"

    missing = m._get_person(db, "does_not_exist")
    assert missing is None


def test_list_shared_memories_filters_private(temp_project_with_migrations):
    from we_together.db.bootstrap import bootstrap_project
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_shared', 'shared_memory', 'public stuff', 0.8, 0.8, 1, 'active',
           '{}', datetime('now'), datetime('now'))"""
    )
    conn.execute(
        """INSERT INTO memories(memory_id, memory_type, summary, relevance_score,
           confidence, is_shared, status, metadata_json, created_at, updated_at)
           VALUES('m_private', 'individual_memory', 'private stuff', 0.8, 0.8, 0,
           'active', '{}', datetime('now'), datetime('now'))"""
    )
    conn.execute(
        "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
        "VALUES('m_shared','person','pFed', NULL)"
    )
    conn.execute(
        "INSERT INTO memory_owners(memory_id, owner_type, owner_id, role_label) "
        "VALUES('m_private','person','pFed', NULL)"
    )
    conn.commit()
    conn.close()

    m = _load_server_module()
    r = m._list_shared_memories(db, owner_id="pFed")
    ids = {x["memory_id"] for x in r["memories"]}
    assert "m_shared" in ids
    assert "m_private" not in ids


def test_federation_client_against_server(temp_project_with_migrations):
    """e2e：真启 HTTP server + client 调 4 个 endpoint"""
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.federation_client import FederationClient
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) VALUES('pE2E','E2E','active',0.9,'{}',"
        "datetime('now'),datetime('now'))"
    )
    conn.commit()
    conn.close()

    m = _load_server_module()
    from http.server import HTTPServer
    server = HTTPServer(("127.0.0.1", 0), m.make_handler(temp_project_with_migrations))
    port = server.server_address[1]
    thr = threading.Thread(target=server.serve_forever, daemon=True)
    thr.start()

    try:
        c = FederationClient(f"http://127.0.0.1:{port}", timeout=3.0)

        cap = c.capabilities()
        assert cap["federation_protocol_version"] in ("1", "1.1")

        persons = c.list_persons()
        assert any(p["person_id"] == "pE2E" for p in persons["persons"])

        p = c.get_person("pE2E")
        assert p and p["primary_name"] == "E2E"

        missing = c.get_person("does_not_exist_xx")
        assert missing is None

        mems = c.list_memories()
        assert "memories" in mems
    finally:
        server.shutdown()
        server.server_close()


def test_skill_schema_v1_still_frozen():
    from we_together.runtime.skill_runtime import SKILL_SCHEMA_VERSION
    assert SKILL_SCHEMA_VERSION == "1"
