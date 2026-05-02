from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def _load_script(script_name: str, module_name: str):
    script_path = REPO_ROOT / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("script_name", "module_name", "service_attr", "argv_tail", "expected_kwargs"),
    [
        (
            "decay.py",
            "decay_phase_70_parallel",
            "decay_states",
            ["--threshold", "0.25", "--limit", "7"],
            {"threshold": 0.25, "limit": 7},
        ),
        (
            "drift.py",
            "drift_phase_70_parallel",
            "drift_relations",
            ["--window-days", "14", "--limit", "9"],
            {"window_days": 14, "limit": 9},
        ),
        (
            "condense_memories.py",
            "condense_phase_70_parallel",
            "condense_memory_clusters",
            ["--max-clusters", "4", "--min-cluster-size", "3"],
            {"max_clusters": 4, "min_cluster_size": 3},
        ),
    ],
)
def test_parallel_maintenance_clis_resolve_tenant_db(
    tmp_path,
    monkeypatch,
    capsys,
    script_name,
    module_name,
    service_attr,
    argv_tail,
    expected_kwargs,
):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.tenant_router import resolve_tenant_root

    root = tmp_path / "parallel_maintenance"
    tenant_root = resolve_tenant_root(root, "alpha")
    bootstrap_project(tenant_root)
    expected_db_path = tenant_root / "db" / "main.sqlite3"

    mod = _load_script(script_name, module_name)
    captured: dict[str, object] = {}

    def fake_service(db_path, **kwargs):
        captured["db_path"] = db_path
        captured["kwargs"] = kwargs
        return {"ok": True}

    monkeypatch.setattr(mod, service_attr, fake_service)
    monkeypatch.setattr(
        "sys.argv",
        [script_name, "--root", str(root), "--tenant-id", "alpha", *argv_tail],
    )

    mod.main()

    assert captured == {"db_path": expected_db_path, "kwargs": expected_kwargs}
    assert json.loads(capsys.readouterr().out) == {"ok": True}


def test_cold_memory_cli_resolves_tenant_db_for_each_subcommand(
    tmp_path,
    monkeypatch,
    capsys,
):
    from we_together.db.bootstrap import bootstrap_project
    from we_together.services.tenant_router import resolve_tenant_root

    root = tmp_path / "parallel_maintenance"
    tenant_root = resolve_tenant_root(root, "alpha")
    bootstrap_project(tenant_root)
    expected_db_path = tenant_root / "db" / "main.sqlite3"

    mod = _load_script("cold_memory.py", "cold_memory_phase_70_parallel")
    captured: dict[str, object] = {}

    def fake_archive(db_path, **kwargs):
        captured["archive"] = {"db_path": db_path, "kwargs": kwargs}
        return {"archived_count": 0}

    def fake_list(db_path):
        captured["list"] = {"db_path": db_path}
        return [{"memory_id": "mem_cold_1"}]

    def fake_restore(db_path, memory_id):
        captured["restore"] = {"db_path": db_path, "memory_id": memory_id}
        return True

    monkeypatch.setattr(mod, "archive_cold_memories", fake_archive)
    monkeypatch.setattr(mod, "list_cold_memories", fake_list)
    monkeypatch.setattr(mod, "restore_cold_memory", fake_restore)

    monkeypatch.setattr(
        "sys.argv",
        [
            "cold_memory.py",
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "archive",
            "--window-days",
            "30",
            "--relevance-threshold",
            "0.2",
        ],
    )
    mod.main()
    assert captured["archive"] == {
        "db_path": expected_db_path,
        "kwargs": {"window_days": 30, "relevance_threshold": 0.2},
    }
    assert json.loads(capsys.readouterr().out) == {"archived_count": 0}

    monkeypatch.setattr(
        "sys.argv",
        ["cold_memory.py", "--root", str(root), "--tenant-id", "alpha", "list"],
    )
    mod.main()
    assert captured["list"] == {"db_path": expected_db_path}
    assert json.loads(capsys.readouterr().out) == [{"memory_id": "mem_cold_1"}]

    monkeypatch.setattr(
        "sys.argv",
        [
            "cold_memory.py",
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "restore",
            "mem_cold_1",
        ],
    )
    mod.main()
    assert captured["restore"] == {
        "db_path": expected_db_path,
        "memory_id": "mem_cold_1",
    }
    assert json.loads(capsys.readouterr().out) == {
        "restored": True,
        "memory_id": "mem_cold_1",
    }
