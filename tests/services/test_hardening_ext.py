from pathlib import Path

import pytest

from we_together.errors import PatchError
from we_together.db.bootstrap import bootstrap_project
from we_together.observability.sinks import (
    OTLPStubSink,
    StdoutSink,
    get_sink,
    set_sink,
)
from we_together.services.event_bus_service import (
    LocalFileBackend,
    NATSStubBackend,
)
from we_together.services.patch_transactional import apply_patches_transactional
from we_together.services.rbac_service import (
    ROLE_SCOPES,
    Role,
    Scope,
    TokenRegistry,
)


# --- patch transactional ---

def test_transactional_bulk_success(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    patches = [{"patch_id": f"pt_{i}", "source_event_id": "src",
                 "target_type": "memory", "target_id": f"m_{i}",
                 "operation": "noop", "payload": {}, "confidence": 0.5,
                 "reason": "test"} for i in range(3)]
    r = apply_patches_transactional(db, patches)
    assert r["applied_count"] == 3
    assert r["failed_count"] == 0


def test_transactional_rolls_back_on_error(temp_project_with_migrations):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    # 第 2 条 patch_id 与第 1 条相同 → PRIMARY KEY 冲突 → 整体 ROLLBACK
    patches = [
        {"patch_id": "dup", "source_event_id": "s", "target_type": "memory",
         "target_id": "m", "operation": "x", "payload": {}, "confidence": 0.5,
         "reason": "r"},
        {"patch_id": "dup", "source_event_id": "s", "target_type": "memory",
         "target_id": "m2", "operation": "x", "payload": {}, "confidence": 0.5,
         "reason": "r"},
    ]
    with pytest.raises(PatchError):
        apply_patches_transactional(db, patches)
    # 第 1 条也被 rollback
    import sqlite3
    c = sqlite3.connect(db)
    rows = c.execute("SELECT patch_id FROM patches WHERE patch_id = 'dup'").fetchall()
    c.close()
    assert rows == []


# --- RBAC ---

def test_rbac_role_scopes():
    assert Scope.READ in ROLE_SCOPES[Role.VIEWER]
    assert Scope.WRITE not in ROLE_SCOPES[Role.VIEWER]
    assert Scope.WRITE in ROLE_SCOPES[Role.EDITOR]
    assert Scope.FEDERATION_ADMIN in ROLE_SCOPES[Role.ADMIN]


def test_rbac_token_registry():
    reg = TokenRegistry()
    reg.register("t1", Role.EDITOR, tenant_id="alpha")
    info = reg.lookup("t1")
    assert info.role == Role.EDITOR
    assert info.tenant_id == "alpha"

    assert reg.check("t1", Scope.WRITE)
    assert not reg.check("t1", Scope.FEDERATION_ADMIN)
    assert not reg.check("nope", Scope.READ)


# --- sinks ---

def test_sink_default_is_stdout():
    assert isinstance(get_sink(), StdoutSink)


def test_otlp_stub_records_calls():
    stub = OTLPStubSink()
    stub.emit_counter("x", 1.0, {"k": "v"})
    stub.emit_log("evt", {"a": 1})
    stub.emit_gauge("g", 42.0, None)
    assert len(stub.calls) == 3
    assert stub.calls[0]["kind"] == "counter"
    assert stub.calls[1]["event"] == "evt"


def test_set_sink_switches(monkeypatch):
    stub = OTLPStubSink()
    set_sink(stub)
    assert get_sink() is stub
    set_sink(StdoutSink())  # reset


# --- event bus backends ---

def test_local_file_backend_roundtrip(tmp_path):
    b = LocalFileBackend(tmp_path / "bus")
    b.publish("t", {"x": 1})
    collected: list = []
    n = b.drain("t", collected.append)
    assert n == 1


def test_nats_stub_publish_records():
    b = NATSStubBackend(server_url="nats://stub")
    eid = b.publish("topic", {"k": "v"})
    assert eid.startswith("nats_stub_")
    assert b.drain("topic", lambda e: None) == 0
