from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from seed_demo import seed_society_c

from we_together.db.bootstrap import bootstrap_project
from we_together.services.tenant_router import resolve_tenant_root


def _python_bin() -> str:
    return str(REPO_ROOT / ".venv" / "bin" / "python")


def test_analyze_cli_supports_tenant_id(tmp_path):
    root = tmp_path / "analysis_proj"
    tenant_root = resolve_tenant_root(root, "alpha")
    bootstrap_project(root)
    bootstrap_project(tenant_root)

    default_db = root / "db" / "main.sqlite3"
    tenant_db = tenant_root / "db" / "main.sqlite3"

    conn = sqlite3.connect(default_db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_default_only', 'Default Only', 'active', 0.9, '{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    conn = sqlite3.connect(tenant_db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_tenant_only', 'Tenant Only', 'active', 0.9, '{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    proc = subprocess.run(
        [
            _python_bin(),
            str(REPO_ROOT / "scripts" / "analyze.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--mode",
            "isolated",
            "--window-days",
            "30",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    names = {row["primary_name"] for row in payload}
    assert "Tenant Only" in names
    assert "Default Only" not in names


def test_eval_relation_cli_supports_tenant_id(tmp_path):
    root = tmp_path / "eval_proj"
    bootstrap_project(root)
    seed_society_c(resolve_tenant_root(root, "alpha"))

    proc = subprocess.run(
        [
            _python_bin(),
            str(REPO_ROOT / "scripts" / "eval_relation.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--benchmark",
            "society_c",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["predicted_count"] >= 1
    assert payload["precision"] >= 0.9
    assert payload["recall"] >= 0.9


def test_bench_large_cli_supports_tenant_id(tmp_path):
    root = tmp_path / "bench_proj"

    proc = subprocess.run(
        [
            _python_bin(),
            str(REPO_ROOT / "scripts" / "bench_large.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--persons",
            "3",
            "--reps",
            "2",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["persons_inserted"] == 3
    assert (root / "tenants" / "alpha" / "db" / "main.sqlite3").exists()
    assert not (root / "db" / "main.sqlite3").exists()
