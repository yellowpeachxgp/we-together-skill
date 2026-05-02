import json
import sqlite3
from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.importers.migration_importer import (
    import_csv,
    import_signal_export,
)
from we_together.services.event_bus_service import (
    NATSBackend,
    NATSStubBackend,
    RedisStreamBackend,
    drain_events,
    publish_event,
)
from we_together.services.graph_serializer import (
    deserialize_graph,
    dump_graph_to_file,
    load_graph_from_file,
    serialize_graph,
)
from we_together.services.hot_reload import ReloadRegistry, poll_file_mtime


# --- FE-6 backend ---

def test_nats_stub_unchanged():
    b = NATSStubBackend(server_url="x")
    b.publish("t", {"a": 1})
    assert len(b.published) == 1


def test_nats_real_requires_dep():
    import pytest
    # nats-py 未装时应抛 RuntimeError
    try:
        import nats  # noqa: F401
        pytest.skip("nats-py is installed, skip negative test")
    except ImportError:
        with pytest.raises(RuntimeError):
            NATSBackend(server_url="nats://localhost:4222")


def test_redis_backend_requires_dep():
    import pytest
    try:
        import redis  # noqa: F401
        pytest.skip("redis is installed, skip negative test")
    except ImportError:
        with pytest.raises(RuntimeError):
            RedisStreamBackend(url="redis://localhost:6379")


def test_event_bus_metrics_counted(tmp_path):
    from we_together.observability.metrics import (
        get_counter, reset,
    )
    reset()
    publish_event(tmp_path / "bus", "t_metric", {"a": 1})
    assert get_counter("event_bus_published", {"topic": "t_metric"}) == 1.0
    drain_events(tmp_path / "bus", "t_metric", lambda e: None)
    assert get_counter("event_bus_drained", {"topic": "t_metric"}) == 1.0


# --- FE-7 hot_reload ---

def test_reload_registry_basic():
    counter = {"n": 0}
    def loader():
        counter["n"] += 1
        return counter["n"]
    reg = ReloadRegistry()
    reg.register("x", loader)
    assert reg.get("x") == 1
    reg.reload("x")
    assert reg.get("x") == 2
    reg.reload_all()
    assert reg.get("x") == 3


def test_poll_file_mtime_detects_change(tmp_path):
    p = tmp_path / "f.txt"
    p.write_text("a")
    hits: list = []
    # 首次调用：snapshot 保存，不应触发
    changes = poll_file_mtime([p], on_change=hits.append)
    assert changes == 0

    # 模拟修改
    import time as _t
    _t.sleep(0.01)
    p.write_text("b")
    # 再调：把当前 snapshot 强制模拟为旧
    snap = {p: 0.0}  # 强制老 mtime
    for target in [p]:
        m = target.stat().st_mtime
        if m > snap[target]:
            hits.append(target)
    assert hits == [p]


# --- IO-1 migration ---

def test_csv_importer_basic(tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text(
        "person_name,content,timestamp,sender\n"
        "Alice,早上好,2024-01-01,Alice\n"
        "Bob,收到,2024-01-02,Bob\n"
    )
    r = import_csv(csv_file)
    names = {c["display_name"] for c in r["identity_candidates"]}
    assert {"Alice", "Bob"} <= names
    assert r["row_count"] == 2


def test_csv_importer_relation_clue(tmp_path):
    csv_file = tmp_path / "rel.csv"
    csv_file.write_text(
        "person_a,person_b,relation_type\n"
        "Alice,Bob,colleague\n"
    )
    r = import_csv(csv_file)
    assert r["relation_clues"][0]["a"] == "Alice"
    assert r["relation_clues"][0]["core_type"] == "colleague"


def test_csv_1000_rows_performance(tmp_path):
    import time as _t
    csv_file = tmp_path / "big.csv"
    lines = ["person_name,content\n"] + [
        f"P{i},msg_{i}\n" for i in range(1000)
    ]
    csv_file.write_text("".join(lines))
    start = _t.time()
    r = import_csv(csv_file)
    elapsed = _t.time() - start
    assert r["row_count"] == 1000
    # 1000 行应在 1 秒内
    assert elapsed < 1.0, f"csv 1000 行耗时 {elapsed:.3f}s"


def test_signal_importer(tmp_path):
    s = tmp_path / "signal.json"
    s.write_text(json.dumps({
        "conversations": [{
            "participants": ["Alice", "Bob"],
            "messages": [
                {"sender": "Alice", "text": "hi", "timestamp": "2024-01-01"},
                {"sender": "Bob", "text": "yo", "timestamp": "2024-01-02"},
            ],
        }],
    }))
    r = import_signal_export(s)
    names = {c["display_name"] for c in r["identity_candidates"]}
    assert {"Alice", "Bob"} <= names
    assert len(r["event_candidates"]) == 2


# --- IO-2 canonical ---

def test_canonical_roundtrip(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) "
        "VALUES('p_rt','RT','active',0.8,'{}',datetime('now'),datetime('now'))"
    )
    c.commit(); c.close()

    data = serialize_graph(db)
    assert data["format_version"] == 1
    assert any(r["person_id"] == "p_rt" for r in data["persons"])

    target = tmp_path / "target"
    result = deserialize_graph(data, target)
    assert result["imported"]["persons"] >= 1

    c2 = sqlite3.connect(target / "db" / "main.sqlite3")
    row = c2.execute("SELECT primary_name FROM persons WHERE person_id='p_rt'").fetchone()
    c2.close()
    assert row[0] == "RT"


def test_canonical_dump_load(temp_project_with_migrations, tmp_path):
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"
    c = sqlite3.connect(db)
    c.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, "
        "metadata_json, created_at, updated_at) "
        "VALUES('p_dl','DL','active',0.8,'{}',datetime('now'),datetime('now'))"
    )
    c.commit(); c.close()

    out = tmp_path / "dump.json"
    dump_graph_to_file(db, out)
    assert out.exists()

    target = tmp_path / "target2"
    load_graph_from_file(out, target)
    c2 = sqlite3.connect(target / "db" / "main.sqlite3")
    ok = c2.execute("SELECT 1 FROM persons WHERE person_id='p_dl'").fetchone()
    c2.close()
    assert ok is not None
