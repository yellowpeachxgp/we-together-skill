from pathlib import Path
import subprocess
import json


def test_cli_workflow_bootstrap_create_scene_import_and_export(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    bootstrap = subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr

    create_scene = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "create_scene.py"),
            "--root",
            str(temp_project_with_migrations),
            "--scene-type",
            "private_chat",
            "--summary",
            "night chat",
            "--location-scope",
            "remote",
            "--channel-scope",
            "private_dm",
            "--visibility-scope",
            "mutual_visible",
            "--participant",
            "person_alice",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert create_scene.returncode == 0, create_scene.stderr
    scene_payload = json.loads(create_scene.stdout)
    scene_id = scene_payload["scene_id"]

    narration = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_narration.py"),
            "--root",
            str(temp_project_with_migrations),
            "--text",
            "小王和小李以前是同事，现在还是朋友。",
            "--source-name",
            "manual-note",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert narration.returncode == 0, narration.stderr

    export_pkg = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "build_retrieval_package.py"),
            "--root",
            str(temp_project_with_migrations),
            "--scene-id",
            scene_id,
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert export_pkg.returncode == 0, export_pkg.stderr
    package = json.loads(export_pkg.stdout)
    assert package["scene_summary"]["scene_id"] == scene_id
    assert package["participants"][0]["person_id"] == "person_alice"
