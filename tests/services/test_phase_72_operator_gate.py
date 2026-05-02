from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

from we_together.db.bootstrap import bootstrap_project
from we_together.services.tenant_router import resolve_tenant_root


def test_unmerge_gate_cli_opens_branch(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[2]
    python = str(repo_root / ".venv" / "bin" / "python")
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_cli_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_cli_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_cli_tgt','tgt','active',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    proc = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "unmerge_gate.py"),
            "--root",
            str(temp_project_with_migrations),
            "--source-person-id",
            "p_cli_src",
            "--reason",
            "manual contradiction review",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["branch_id"].startswith("branch_unmerge_")
    assert payload["unmerge_candidate_id"].startswith("cand_unmerge_")


def test_unmerge_gate_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    python = str(repo_root / ".venv" / "bin" / "python")
    tenant_root = resolve_tenant_root(tmp_path, "alpha")
    bootstrap_project(tenant_root)
    db = tenant_root / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_cli_tenant_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_cli_tenant_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_cli_tenant_tgt','tgt','active',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    proc = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "unmerge_gate.py"),
            "--root",
            str(tmp_path),
            "--tenant-id",
            "alpha",
            "--source-person-id",
            "p_cli_tenant_src",
            "--reason",
            "tenant contradiction review",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)

    conn = sqlite3.connect(db)
    branch = conn.execute(
        "SELECT branch_id FROM local_branches WHERE branch_id = ?",
        (payload["branch_id"],),
    ).fetchone()
    conn.close()

    assert branch is not None


def test_unmerge_gate_cli_rejects_non_active_target(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[2]
    python = str(repo_root / ".venv" / "bin" / "python")
    bootstrap_project(temp_project_with_migrations)
    db = temp_project_with_migrations / "db" / "main.sqlite3"

    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_cli_bad_src','src','merged',0.5, ?, datetime('now'), datetime('now'))",
        (json.dumps({"merged_into": "p_cli_bad_tgt"}),),
    )
    conn.execute(
        "INSERT INTO persons(person_id, primary_name, status, confidence, metadata_json, created_at, updated_at) "
        "VALUES('p_cli_bad_tgt','tgt','inactive',0.8,'{}', datetime('now'), datetime('now'))"
    )
    conn.commit()
    conn.close()

    proc = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "unmerge_gate.py"),
            "--root",
            str(temp_project_with_migrations),
            "--source-person-id",
            "p_cli_bad_src",
            "--reason",
            "inactive target should fail",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert "merged_into target is not active" in payload["error"]
