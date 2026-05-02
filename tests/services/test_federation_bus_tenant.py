import json
from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.services.event_bus_service import (
    drain_events,
    peek_events,
    publish_event,
)
from we_together.services.federation_service import (
    get_eager_refs,
    list_external_refs,
    register_external_person,
)
from we_together.services.tenant_router import (
    DEFAULT_TENANT_ID,
    infer_tenant_id_from_db_path,
    infer_tenant_id_from_root,
    normalize_tenant_id,
    resolve_tenant_db_path,
    resolve_tenant_root,
)

# --- Federation ---

def test_federation_register_and_list(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    rid = register_external_person(
        db_path, external_skill_name="partner-skill",
        external_person_id="p_ext_1", display_name="Remote Alice",
        trust_level=0.8, policy="eager",
    )
    assert rid.startswith("extref_")
    refs = list_external_refs(db_path)
    assert len(refs) == 1
    assert refs[0]["display_name"] == "Remote Alice"

    eager = get_eager_refs(db_path)
    assert len(eager) == 1


def test_federation_unique_per_external_id(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"
    register_external_person(db_path, external_skill_name="s1",
                              external_person_id="p1", display_name="A")
    register_external_person(db_path, external_skill_name="s1",
                              external_person_id="p1", display_name="A2")
    # 第二次 REPLACE 应覆盖，总数仍为 1
    refs = list_external_refs(db_path)
    assert len(refs) == 1
    assert refs[0]["display_name"] == "A2"


# --- Event bus ---

def test_event_bus_publish_and_drain(tmp_path):
    bus = tmp_path / "bus"
    publish_event(bus, "scene.evolved", {"scene_id": "s1", "delta": 1})
    publish_event(bus, "scene.evolved", {"scene_id": "s2", "delta": 2})
    collected = []
    n = drain_events(bus, "scene.evolved", collected.append)
    assert n == 2
    # 二次 drain 应是 0（cursor 推进）
    n2 = drain_events(bus, "scene.evolved", collected.append)
    assert n2 == 0


def test_event_bus_peek(tmp_path):
    bus = tmp_path / "bus"
    for i in range(3):
        publish_event(bus, "x", {"i": i})
    peek = peek_events(bus, "x", limit=2)
    assert len(peek) == 2
    assert peek[-1]["payload"]["i"] == 2


# --- Tenant ---

def test_tenant_router_default(tmp_path):
    assert resolve_tenant_db_path(tmp_path) == tmp_path / "db" / "main.sqlite3"
    assert resolve_tenant_root(tmp_path) == tmp_path


def test_tenant_router_named(tmp_path):
    db = resolve_tenant_db_path(tmp_path, "alpha")
    assert db == tmp_path / "tenants" / "alpha" / "db" / "main.sqlite3"
    root = resolve_tenant_root(tmp_path, "alpha")
    assert root == tmp_path / "tenants" / "alpha"


def test_tenant_router_normalizes_default_like_values(tmp_path):
    assert normalize_tenant_id(None) == DEFAULT_TENANT_ID
    assert normalize_tenant_id("") == DEFAULT_TENANT_ID
    assert normalize_tenant_id("   ") == DEFAULT_TENANT_ID
    assert resolve_tenant_root(tmp_path, " default ".strip()) == tmp_path


def test_tenant_router_rejects_invalid_ids(tmp_path):
    import pytest

    for bad in ("..", ".", "../evil", "alpha/beta", "alpha\\beta", "alpha beta", "a*b"):
        with pytest.raises(ValueError, match="invalid tenant_id"):
            resolve_tenant_root(tmp_path, bad)
        with pytest.raises(ValueError, match="invalid tenant_id"):
            resolve_tenant_db_path(tmp_path, bad)


def test_tenant_router_infers_ids(tmp_path):
    assert infer_tenant_id_from_root(tmp_path) == DEFAULT_TENANT_ID
    tenant_root = resolve_tenant_root(tmp_path, "alpha")
    assert infer_tenant_id_from_root(tenant_root) == "alpha"
    assert infer_tenant_id_from_db_path(tenant_root / "db" / "main.sqlite3") == "alpha"
