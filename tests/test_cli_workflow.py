import json
import subprocess
from pathlib import Path


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


def test_build_retrieval_package_cli_reports_missing_scene_cleanly(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    bootstrap = subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert bootstrap.returncode == 0, bootstrap.stderr

    export_pkg = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "build_retrieval_package.py"),
            "--root",
            str(temp_project_with_migrations),
            "--scene-id",
            "scene_missing",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )

    assert export_pkg.returncode != 0
    assert export_pkg.stdout == ""
    assert export_pkg.stderr.strip() == "Scene not found: scene_missing"


def test_build_retrieval_package_cli_accepts_input_hash_for_cache(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    create_scene = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "create_scene.py"),
            "--root",
            str(temp_project_with_migrations),
            "--scene-type",
            "private_chat",
            "--summary",
            "cached cli scene",
            "--location-scope",
            "remote",
            "--channel-scope",
            "private_dm",
            "--visibility-scope",
            "mutual_visible",
            "--participant",
            "person_cache_cli",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    scene_id = json.loads(create_scene.stdout)["scene_id"]

    first_run = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "build_retrieval_package.py"),
            "--root",
            str(temp_project_with_migrations),
            "--scene-id",
            scene_id,
            "--input-hash",
            "cli_hash_1",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert first_run.returncode == 0, first_run.stderr

    second_run = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "build_retrieval_package.py"),
            "--root",
            str(temp_project_with_migrations),
            "--scene-id",
            scene_id,
            "--input-hash",
            "cli_hash_1",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert second_run.returncode == 0, second_run.stderr
    assert json.loads(first_run.stdout) == json.loads(second_run.stdout)


def test_cli_workflow_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "tenant_proj"

    subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "bootstrap.py"),
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

    create_scene = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "create_scene.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--scene-type",
            "private_chat",
            "--summary",
            "tenant chat",
            "--location-scope",
            "remote",
            "--channel-scope",
            "private_dm",
            "--visibility-scope",
            "mutual_visible",
            "--participant",
            "person_alpha",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    scene_id = json.loads(create_scene.stdout)["scene_id"]

    narration = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "import_narration.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--text",
            "小王和小李以前是同事，现在还是朋友。",
            "--source-name",
            "tenant-note",
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
            str(root),
            "--tenant-id",
            "alpha",
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

    default_pkg = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "build_retrieval_package.py"),
            "--root",
            str(root),
            "--scene-id",
            scene_id,
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert default_pkg.returncode != 0


def test_dialogue_turn_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "tenant_dialogue"

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

    scene_id = "scene_missing"
    # 从 tenant root 读取一个真实 scene
    tenant_graph = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "graph_summary.py"),
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
    assert json.loads(tenant_graph.stdout)["scene_count"] >= 1

    import sqlite3
    tenant_db = root / "tenants" / "alpha" / "db" / "main.sqlite3"
    conn = sqlite3.connect(tenant_db)
    scene_id = conn.execute("SELECT scene_id FROM scenes LIMIT 1").fetchone()[0]
    conn.close()

    turn = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "dialogue_turn.py"),
            "--root",
            str(root),
            "--tenant-id",
            "alpha",
            "--scene-id",
            scene_id,
            "--user-input",
            "tenant dialogue",
            "--response-text",
            "tenant reply",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    payload = json.loads(turn.stdout)
    assert payload["retrieval_package"]["scene_summary"]["scene_id"] == scene_id

    default_turn = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "dialogue_turn.py"),
            "--root",
            str(root),
            "--scene-id",
            scene_id,
            "--user-input",
            "tenant dialogue",
            "--response-text",
            "tenant reply",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert default_turn.returncode != 0
