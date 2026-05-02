import json
import subprocess
from pathlib import Path


def test_group_cli_creates_group_and_members(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    result = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "create_group.py"),
            "--root",
            str(temp_project_with_migrations),
            "--group-type",
            "team",
            "--name",
            "核心团队",
            "--summary",
            "主开发小组",
            "--member",
            "person_alice:owner",
            "--member",
            "person_bob:member",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["group_id"].startswith("group_")
    assert payload["member_count"] == 2


def test_group_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "tenant_group"

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(root), "--tenant-id", "alpha"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    result = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "create_group.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--group-type",
            "team",
            "--name",
            "Alpha 团队",
            "--summary",
            "tenant group",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["group_id"].startswith("group_")
