import json
import subprocess
from pathlib import Path


def test_directory_import_cli_imports_supported_files(temp_project_with_migrations, tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    (tmp_path / "note.txt").write_text("小王和小李以前是同事，现在还是朋友。", encoding="utf-8")
    (tmp_path / "mail.eml").write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Project Update\n"
        "Date: Mon, 06 Apr 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "今天的项目推进顺利。\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_directory.py"),
            "--root",
            str(temp_project_with_migrations),
            "--dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["file_count"] == 2


def test_directory_import_cli_reports_missing_directory_cleanly(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    missing_dir = temp_project_with_migrations / "missing-dir"
    result = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_directory.py"),
            "--root",
            str(temp_project_with_migrations),
            "--dir",
            str(missing_dir),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr.strip() == f"Directory not found: {missing_dir}"


def test_directory_import_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "tenant_directory"

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(root), "--tenant-id", "alpha"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    (tmp_path / "note.txt").write_text("小王和小李以前是同事，现在还是朋友。", encoding="utf-8")
    result = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_directory.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["file_count"] >= 1
