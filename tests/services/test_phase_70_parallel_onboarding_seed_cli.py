from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def test_seed_society_m_cli_supports_tenant_id(tmp_path):
    root = tmp_path / "seed_m_tenant"
    proc = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts" / "seed_society_m.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--n",
            "12",
            "--seed-value",
            "7",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["persons"] == 12

    db = root / "tenants" / "alpha" / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0] == 12
    conn.close()


def test_seed_society_l_cli_supports_tenant_id(tmp_path):
    root = tmp_path / "seed_l_tenant"
    proc = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts" / "seed_society_l.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--n",
            "15",
            "--seed-value",
            "11",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["persons"] == 15

    db = root / "tenants" / "alpha" / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0] == 15
    conn.close()


def test_onboard_cli_preserves_tenant_id_in_suggested_commands(tmp_path):
    root = tmp_path / "onboard_tenant"
    proc = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts" / "onboard.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
        ],
        input="\n1\n\n\n\n",
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )

    assert proc.returncode == 0, proc.stderr
    assert "we-together bootstrap --root" in proc.stdout
    assert "--tenant-id alpha" in proc.stdout
    assert "we-together ingest narration" in proc.stdout
    assert "we-together create-scene" in proc.stdout
    assert "we-together graph-summary" in proc.stdout
