import json
import subprocess
from pathlib import Path


def test_auto_import_cli_detects_and_imports_text_chat(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    transcript = "2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n"
    result = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_auto.py"),
            "--root",
            str(temp_project_with_migrations),
            "--source-name",
            "chat.txt",
            "--text",
            transcript,
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "text_chat"


def test_auto_import_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "tenant_auto"

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(root), "--tenant-id", "alpha"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    transcript = "2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n"
    result = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_auto.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--source-name",
            "tenant_chat.txt",
            "--text",
            transcript,
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "text_chat"
