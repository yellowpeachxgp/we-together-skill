import json
import subprocess
from pathlib import Path


def test_text_chat_cli_imports_transcript_into_graph(temp_project_with_migrations):
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
    imported = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_text_chat.py"),
            "--root",
            str(temp_project_with_migrations),
            "--source-name",
            "chat.txt",
            "--transcript",
            transcript,
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert imported.returncode == 0, imported.stderr
    payload = json.loads(imported.stdout)
    assert payload["event_count"] >= 2


def test_text_chat_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "tenant_text_chat"

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(root), "--tenant-id", "alpha"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    transcript = "2026-04-06 23:10 小王: 今天好累\n2026-04-06 23:11 小李: 早点休息\n"
    imported = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_text_chat.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--source-name",
            "tenant_chat.txt",
            "--transcript",
            transcript,
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert imported.returncode == 0, imported.stderr
    payload = json.loads(imported.stdout)
    assert payload["event_count"] >= 2
