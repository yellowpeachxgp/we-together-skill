import json
import subprocess
from pathlib import Path


def test_email_cli_imports_eml_into_graph(temp_project_with_migrations, tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    eml_path = tmp_path / "sample.eml"
    eml_path.write_text(
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
            str(repo_root / "scripts" / "import_email_file.py"),
            "--root",
            str(temp_project_with_migrations),
            "--file",
            str(eml_path),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["import_job_id"].startswith("import_")


def test_email_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "tenant_email"

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(root), "--tenant-id", "alpha"],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    eml_path = tmp_path / "sample.eml"
    eml_path.write_text(
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
            str(repo_root / "scripts" / "import_email_file.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--file",
            str(eml_path),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["import_job_id"].startswith("import_")
