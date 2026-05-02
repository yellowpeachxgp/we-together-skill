from __future__ import annotations

import importlib.util
import json
import sqlite3
import subprocess
import sys
import threading
from http.server import HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _load_bootstrap_script():
    p = REPO_ROOT / "scripts" / "bootstrap.py"
    spec = importlib.util.spec_from_file_location("bootstrap_phase_70", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_seed_demo_script():
    p = REPO_ROOT / "scripts" / "seed_demo.py"
    spec = importlib.util.spec_from_file_location("seed_demo_phase_70", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_fed_server():
    p = REPO_ROOT / "scripts" / "federation_http_server.py"
    spec = importlib.util.spec_from_file_location("fed_phase_70", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_branch_console():
    p = REPO_ROOT / "scripts" / "branch_console.py"
    spec = importlib.util.spec_from_file_location("branch_console_phase_70", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bootstrap_script_supports_tenant_id(tmp_path, monkeypatch):
    mod = _load_bootstrap_script()
    root = tmp_path / "proj"
    monkeypatch.setattr(
        "sys.argv",
        ["bootstrap.py", "--root", str(root), "--tenant-id", "alpha"],
    )
    mod.main()
    assert (root / "tenants" / "alpha" / "db" / "main.sqlite3").exists()


def test_bootstrap_script_rejects_invalid_tenant_id(tmp_path):
    repo_root = REPO_ROOT
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "proj"
    proc = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "bootstrap.py"),
            "--root",
            str(root),
            "--tenant-id",
            "../evil",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert proc.returncode != 0
    assert "invalid tenant_id" in proc.stderr


def test_seed_demo_supports_tenant_id(tmp_path, monkeypatch):
    mod = _load_seed_demo_script()
    root = tmp_path / "proj"
    monkeypatch.setattr(
        "sys.argv",
        ["seed_demo.py", "--root", str(root), "--tenant-id", "alpha"],
    )
    mod.main()
    db = root / "tenants" / "alpha" / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    conn.close()
    assert person_count >= 8


def test_federation_server_reads_tenant_db(tmp_path):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.federation_client import FederationClient
    from we_together.services.tenant_router import resolve_tenant_root

    root = tmp_path / "proj"
    bootstrap_project(root)
    tenant_root = resolve_tenant_root(root, "alpha")
    bootstrap_project(tenant_root)

    default_db = root / "db" / "main.sqlite3"
    tenant_db = tenant_root / "db" / "main.sqlite3"

    conn = sqlite3.connect(default_db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_default', 'Default User', 'active', 0.9, '{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    conn = sqlite3.connect(tenant_db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_alpha', 'Alpha User', 'active', 0.9, '{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    mod = _load_fed_server()
    server = HTTPServer(
        ("127.0.0.1", 0),
        mod.make_handler(tenant_root, allow_writes=False),
    )
    port = server.server_address[1]
    thr = threading.Thread(target=server.serve_forever, daemon=True)
    thr.start()
    try:
        client = FederationClient(f"http://127.0.0.1:{port}")
        persons = client.list_persons()
        names = {p["primary_name"] for p in persons["persons"]}
        assert "Alpha User" in names
        assert "Default User" not in names
    finally:
        server.shutdown()
        server.server_close()


def test_operational_scripts_support_tenant_id(tmp_path):
    repo_root = REPO_ROOT
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "ops_tenant"

    subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "seed_demo.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    for script_args in [
        [
            str(repo_root / "scripts" / "simulate_week.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--ticks",
            "1",
            "--budget",
            "0",
        ],
        [
            str(repo_root / "scripts" / "simulate_year.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--days",
            "1",
            "--budget",
            "0",
        ],
        [
            str(repo_root / "scripts" / "dream_cycle.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--lookback",
            "7",
        ],
        [
            str(repo_root / "scripts" / "fix_graph.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--policy",
            "report_only",
        ],
    ]:
        proc = subprocess.run(
            [python, *script_args],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        assert proc.returncode == 0, proc.stderr


def test_management_scripts_support_tenant_id(tmp_path, monkeypatch):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.activation_trace_service import record
    from we_together.services.dialogue_service import record_dialogue_event
    from we_together.services.scene_service import create_scene
    from we_together.services.tenant_router import resolve_tenant_root

    repo_root = REPO_ROOT
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "mgmt_tenant"
    tenant_root = resolve_tenant_root(root, "alpha")
    bootstrap_project(tenant_root)
    db = tenant_root / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.executemany(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES(?, ?, 'active', 0.9, '{}', datetime('now'), datetime('now'))",
        [("p_a", "Alice"), ("p_b", "Bob"), ("p_dup_1", "小明"), ("p_dup_2", "小明")],
    )
    conn.executemany(
        "INSERT INTO identity_links(identity_id, person_id, platform, external_id, display_name, confidence, "
        "is_user_confirmed, is_active, metadata_json, created_at, updated_at) "
        "VALUES(?, ?, ?, ?, ?, 0.8, 0, 1, '{}', datetime('now'), datetime('now'))",
        [
            ("id_dup_1", "p_dup_1", "wechat", "xm1", "小明"),
            ("id_dup_2", "p_dup_2", "email", "xm2", "小明"),
        ],
    )
    conn.execute(
        "INSERT INTO local_branches(branch_id, scope_type, scope_id, status, reason, created_at) "
        "VALUES('br_tenant', 'person', 'p_a', 'open', 'tenant test', datetime('now'))"
    )
    conn.executemany(
        "INSERT INTO branch_candidates(candidate_id, branch_id, label, confidence, payload_json, status, created_at) "
        "VALUES(?, 'br_tenant', ?, ?, '{}', 'open', datetime('now'))",
        [("cand_hi", "hi", 0.95), ("cand_lo", "lo", 0.10)],
    )
    conn.commit()
    conn.close()

    scene_id = create_scene(
        db_path=db,
        scene_type="private_chat",
        scene_summary="tenant snapshot scene",
        environment={"location_scope": "remote", "channel_scope": "private_dm", "visibility_scope": "mutual_visible"},
    )
    record_dialogue_event(db, scene_id=scene_id, user_input="hi", response_text="ok", speaking_person_ids=[])
    record(
        db,
        from_entity_type="person",
        from_entity_id="p_a",
        to_entity_type="person",
        to_entity_id="p_b",
        weight=1.0,
    )

    branch_console = _load_branch_console()
    captured = {}

    class _DummyServer:
        def serve_forever(self):  # pragma: no cover - only wiring
            return None

        def server_close(self):
            return None

    def _fake_serve(db_path, host, port, token=None):
        captured["db_path"] = db_path
        return _DummyServer()

    monkeypatch.setattr(branch_console, "serve", _fake_serve)
    monkeypatch.setattr(
        "sys.argv",
        ["branch_console.py", "--root", str(root), "--tenant-id", "alpha"],
    )
    branch_console.main()
    assert captured["db_path"] == tenant_root / "db" / "main.sqlite3"

    cmd_groups = [
        [
            str(repo_root / "scripts" / "snapshot.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "list",
        ],
        [
            str(repo_root / "scripts" / "world_cli.py"),
            "register-place",
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--name",
            "Tenant Place",
        ],
        [
            str(repo_root / "scripts" / "activation_path.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--from",
            "p_a",
            "--to",
            "p_b",
        ],
        [
            str(repo_root / "scripts" / "auto_resolve_branches.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--threshold",
            "0.8",
            "--margin",
            "0.2",
        ],
        [
            str(repo_root / "scripts" / "merge_duplicates.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
        ],
    ]

    outputs = []
    for args in cmd_groups:
        proc = subprocess.run([python, *args], capture_output=True, text=True, cwd=repo_root)
        assert proc.returncode == 0, proc.stderr
        outputs.append(json.loads(proc.stdout))

    snapshot_list, place_result, path_result, resolve_result, merge_result = outputs
    assert snapshot_list and snapshot_list[0]["snapshot_id"].startswith("snap_")
    assert place_result["place_id"].startswith("place_")
    assert path_result["count"] >= 1
    assert resolve_result["resolved_count"] == 1
    assert merge_result["merged_count"] >= 1


def test_maintenance_and_agent_scripts_support_tenant_id(tmp_path):
    repo_root = REPO_ROOT
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "agent_tenant"

    seed = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "seed_demo.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    seed_payload = json.loads(seed.stdout)
    scene_id = seed_payload["scenes"]["work"]

    for args in [
        [
            str(repo_root / "scripts" / "daily_maintenance.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--skip-llm",
            "--skip-warm",
        ],
        [
            str(repo_root / "scripts" / "agent_chat.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--scene-id",
            scene_id,
            "--input",
            "tenant hello",
            "--max-iters",
            "1",
        ],
        [
            str(repo_root / "scripts" / "multi_agent_chat.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--scene",
            scene_id,
            "--turns",
            "1",
        ],
        [
            str(repo_root / "scripts" / "scenario_runner.py"),
            "--root",
            str(root / "scenario_base"),
            "--tenant-id",
            "alpha",
            "--scenario",
            "family",
        ],
    ]:
        proc = subprocess.run(
            [python, *args],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        assert proc.returncode == 0, proc.stderr


def test_timeline_and_embedding_scripts_support_tenant_id(tmp_path):
    repo_root = REPO_ROOT
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "timeline_tenant"

    seed = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "seed_demo.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    seed_payload = json.loads(seed.stdout)
    alice_id = seed_payload["persons"]["alice"]
    relation_id = seed_payload["relations"]["alice_bob_colleague"]
    scene_id = seed_payload["scenes"]["work"]

    for args in [
        [
            str(repo_root / "scripts" / "embed_backfill.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--target",
            "memory",
            "--limit",
            "5",
        ],
        [
            str(repo_root / "scripts" / "timeline.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--person-id",
            alice_id,
        ],
        [
            str(repo_root / "scripts" / "relation_timeline.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--relation-id",
            relation_id,
        ],
        [
            str(repo_root / "scripts" / "self_activate.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--scene-id",
            scene_id,
            "--daily-budget",
            "1",
            "--per-run",
            "1",
            "--provider",
            "mock",
        ],
        [
            str(repo_root / "scripts" / "extract_facets.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--person-id",
            alice_id,
            "--provider",
            "mock",
            "--max-events",
            "5",
        ],
        [
            str(repo_root / "scripts" / "rollback_tick.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--snapshot",
            "snap_missing",
        ],
    ]:
        proc = subprocess.run(
            [python, *args],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        if args[0].endswith("rollback_tick.py"):
            assert proc.returncode != 0
            assert "error" in proc.stdout
        else:
            assert proc.returncode == 0, proc.stderr
