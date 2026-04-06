from pathlib import Path
import json
import subprocess


def test_file_auto_import_cli_routes_eml_and_txt(temp_project_with_migrations, tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    txt = tmp_path / "sample.txt"
    txt.write_text("小王和小李以前是同事，现在还是朋友。", encoding="utf-8")
    txt_run = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_file_auto.py"),
            "--root",
            str(temp_project_with_migrations),
            "--file",
            str(txt),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert txt_run.returncode == 0, txt_run.stderr
    assert json.loads(txt_run.stdout)["mode"] == "text"

    eml = tmp_path / "sample.eml"
    eml.write_text(
        "From: Alice <alice@example.com>\n"
        "To: Bob <bob@example.com>\n"
        "Subject: Project Update\n"
        "Date: Mon, 06 Apr 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        "今天的项目推进顺利。\n",
        encoding="utf-8",
    )
    eml_run = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_file_auto.py"),
            "--root",
            str(temp_project_with_migrations),
            "--file",
            str(eml),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert eml_run.returncode == 0, eml_run.stderr
    assert json.loads(eml_run.stdout)["mode"] == "email"
