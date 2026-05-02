from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path


def test_graph_io_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "graphio_root"
    out = tmp_path / "graph.json"
    target = tmp_path / "graphio_target"

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

    export_proc = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "graph_io.py"),
            "export",
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    export_payload = json.loads(export_proc.stdout)
    assert export_payload["row_count"] > 0
    assert out.exists()

    import_proc = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "graph_io.py"),
            "import",
            "--input",
            str(out),
            "--target",
            str(target),
            "--tenant-id",
            "beta",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    payload = json.loads(import_proc.stdout)
    assert "tenants/beta/db/main.sqlite3" in payload["target"]

    conn = sqlite3.connect(target / "tenants" / "beta" / "db" / "main.sqlite3")
    person_count = conn.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    conn.close()
    assert person_count >= 8
