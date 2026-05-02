from __future__ import annotations

import json
import sqlite3
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = str(REPO_ROOT / ".venv" / "bin" / "python")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def _bootstrap_default_root(root: Path) -> None:
    proc = _run_cli(
        str(REPO_ROOT / "scripts" / "bootstrap.py"),
        "--root",
        str(root),
    )
    assert proc.returncode == 0, proc.stderr


def _seed_tenant(root: Path, tenant_id: str = "alpha") -> dict:
    proc = _run_cli(
        str(REPO_ROOT / "scripts" / "seed_demo.py"),
        "--root",
        str(root),
        "--tenant-id",
        tenant_id,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _tenant_db(root: Path, tenant_id: str = "alpha") -> Path:
    return root / "tenants" / tenant_id / "db" / "main.sqlite3"


def _insert_narrative_arc(root: Path, scene_id: str, tenant_id: str = "alpha") -> None:
    db = _tenant_db(root, tenant_id)
    conn = sqlite3.connect(db)
    event_ids = [
        row[0]
        for row in conn.execute(
            "SELECT event_id FROM events ORDER BY created_at LIMIT 2",
        ).fetchall()
    ]
    assert len(event_ids) == 2

    arc_id = "arc_tenant_cli"
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO narrative_arcs(
            arc_id, title, summary, theme, start_at, end_at, scene_id, metadata_json, created_at
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            arc_id,
            "Tenant Arc",
            "Arc stored in the tenant-scoped database",
            "tenant-test",
            now,
            now,
            scene_id,
            "{}",
            now,
        ),
    )
    for ordering, event_id in enumerate(event_ids):
        conn.execute(
            "INSERT INTO narrative_arc_events(arc_id, event_id, ordering) VALUES(?, ?, ?)",
            (arc_id, event_id, ordering),
        )
    conn.commit()
    conn.close()


def test_simulate_cli_supports_tenant_id(tmp_path):
    root = tmp_path / "parallel_simulate"
    _bootstrap_default_root(root)
    seed_payload = _seed_tenant(root)
    scene_id = seed_payload["scenes"]["work"]

    tenant_proc = _run_cli(
        str(REPO_ROOT / "scripts" / "simulate.py"),
        "scene-script",
        "--root",
        str(root),
        "--tenant-id",
        "alpha",
        "--scene-id",
        scene_id,
        "--turns",
        "2",
    )
    assert tenant_proc.returncode == 0, tenant_proc.stderr
    tenant_payload = json.loads(tenant_proc.stdout)
    assert tenant_payload["scene_id"] == scene_id
    assert "turn_count" in tenant_payload

    default_proc = _run_cli(
        str(REPO_ROOT / "scripts" / "simulate.py"),
        "scene-script",
        "--root",
        str(root),
        "--scene-id",
        scene_id,
        "--turns",
        "2",
    )
    assert default_proc.returncode != 0
    assert "Scene not found" in default_proc.stderr


def test_what_if_cli_supports_tenant_id(tmp_path):
    root = tmp_path / "parallel_what_if"
    _bootstrap_default_root(root)
    seed_payload = _seed_tenant(root)
    scene_id = seed_payload["scenes"]["work"]

    tenant_proc = _run_cli(
        str(REPO_ROOT / "scripts" / "what_if.py"),
        "--root",
        str(root),
        "--tenant-id",
        "alpha",
        "--scene-id",
        scene_id,
        "--hypothesis",
        "Alice resigns from the team",
    )
    assert tenant_proc.returncode == 0, tenant_proc.stderr
    tenant_payload = json.loads(tenant_proc.stdout)
    assert tenant_payload["scene_id"] == scene_id
    assert tenant_payload["hypothesis"] == "Alice resigns from the team"
    assert tenant_payload["mock_mode"] is True

    default_proc = _run_cli(
        str(REPO_ROOT / "scripts" / "what_if.py"),
        "--root",
        str(root),
        "--scene-id",
        scene_id,
        "--hypothesis",
        "Alice resigns from the team",
    )
    assert default_proc.returncode != 0
    assert "Scene not found" in default_proc.stderr


def test_narrate_cli_supports_tenant_id(tmp_path):
    root = tmp_path / "parallel_narrate"
    _bootstrap_default_root(root)
    seed_payload = _seed_tenant(root)
    scene_id = seed_payload["scenes"]["work"]
    _insert_narrative_arc(root, scene_id)

    tenant_proc = _run_cli(
        str(REPO_ROOT / "scripts" / "narrate.py"),
        "list",
        "--root",
        str(root),
        "--tenant-id",
        "alpha",
        "--scene-id",
        scene_id,
    )
    assert tenant_proc.returncode == 0, tenant_proc.stderr
    tenant_payload = json.loads(tenant_proc.stdout)
    assert len(tenant_payload) == 1
    assert tenant_payload[0]["title"] == "Tenant Arc"
    assert tenant_payload[0]["event_ids"]

    default_proc = _run_cli(
        str(REPO_ROOT / "scripts" / "narrate.py"),
        "list",
        "--root",
        str(root),
        "--scene-id",
        scene_id,
    )
    assert default_proc.returncode == 0, default_proc.stderr
    assert json.loads(default_proc.stdout) == []
