import json
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from graph_summary import build_graph_summary

from we_together.db.bootstrap import bootstrap_project
from we_together.services.patch_applier import apply_patch_record
from we_together.services.patch_service import build_patch


def test_graph_summary_cli_shows_people_and_relations(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
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
        check=True,
    )
    graph = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "graph_summary.py"),
            "--root",
            str(temp_project_with_migrations),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert graph.returncode == 0, graph.stderr
    payload = json.loads(graph.stdout)
    assert payload["tenant_id"] == "default"
    assert payload["person_count"] >= 2
    assert payload["identity_count"] >= 2
    assert payload["relation_count"] >= 1


def test_graph_summary_cli_reports_branch_snapshot_and_runtime_counts(temp_project_with_migrations):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")

    subprocess.run(
        [python, str(repo_root / "scripts" / "bootstrap.py"), "--root", str(temp_project_with_migrations)],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
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
            "graph summary scene",
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
        check=True,
    )
    scene_id = json.loads(create_scene.stdout)["scene_id"]

    subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "build_retrieval_package.py"),
            "--root",
            str(temp_project_with_migrations),
            "--scene-id",
            scene_id,
            "--input-hash",
            "graph_summary_hash",
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

    graph = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "graph_summary.py"),
            "--root",
            str(temp_project_with_migrations),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert graph.returncode == 0, graph.stderr
    payload = json.loads(graph.stdout)

    assert payload["snapshot_entity_count"] >= 1
    assert payload["retrieval_cache_count"] >= 1
    assert payload["scene_active_relation_count"] >= 0
    assert payload["open_local_branch_count"] == 0


def test_graph_summary_includes_candidate_status_distribution(temp_project_with_migrations):
    """验证返回包含 candidate_status_distribution 字段。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_branch_gs",
            target_type="local_branch",
            target_id="branch_gs_1",
            operation="create_local_branch",
            payload={
                "branch_id": "branch_gs_1",
                "scope_type": "scene",
                "scope_id": "scene_gs_1",
                "status": "open",
                "reason": "graph summary test",
                "created_from_event_id": "evt_branch_gs",
                "branch_candidates": [
                    {
                        "candidate_id": "cand_gs_a",
                        "label": "A",
                        "payload_json": {},
                        "confidence": 0.5,
                        "status": "open",
                    },
                    {
                        "candidate_id": "cand_gs_b",
                        "label": "B",
                        "payload_json": {},
                        "confidence": 0.6,
                        "status": "open",
                    },
                ],
            },
            confidence=0.5,
            reason="graph summary branch",
        ),
    )

    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_resolve_gs",
            target_type="local_branch",
            target_id="branch_gs_1",
            operation="resolve_local_branch",
            payload={
                "branch_id": "branch_gs_1",
                "status": "resolved",
                "reason": "resolved for test",
                "selected_candidate_id": "cand_gs_a",
            },
            confidence=0.8,
            reason="resolve branch",
        ),
    )

    summary = build_graph_summary(db_path)
    assert summary["tenant_id"] == "default"
    dist = summary["candidate_status_distribution"]
    assert dist["selected"] == 1
    assert dist["rejected"] == 1
    assert dist.get("open", 0) == 0


def test_graph_summary_includes_extended_counts(temp_project_with_migrations):
    """验证返回包含 memory_count, state_count, patch_count 字段。"""
    bootstrap_project(temp_project_with_migrations)
    db_path = temp_project_with_migrations / "db" / "main.sqlite3"

    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_gs_state",
            target_type="state",
            target_id="state_gs_1",
            operation="update_state",
            payload={
                "state_id": "state_gs_1",
                "scope_type": "scene",
                "scope_id": "scene_gs_2",
                "state_type": "mood",
                "value_json": {"mood": "calm"},
            },
            confidence=0.7,
            reason="state for graph summary",
        ),
    )
    apply_patch_record(
        db_path=db_path,
        patch=build_patch(
            source_event_id="evt_gs_memory",
            target_type="memory",
            target_id="memory_gs_1",
            operation="create_memory",
            payload={
                "memory_id": "memory_gs_1",
                "memory_type": "shared_memory",
                "summary": "graph summary memory",
                "confidence": 0.8,
                "is_shared": 1,
                "status": "active",
            },
            confidence=0.8,
            reason="memory for graph summary",
        ),
    )

    summary = build_graph_summary(db_path)
    assert summary["memory_count"] >= 1
    assert summary["state_count"] >= 1
    assert summary["patch_count"] >= 2


def test_graph_summary_cli_supports_tenant_id(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    python = str(repo_root / ".venv" / "bin" / "python")
    root = tmp_path / "tenant_graph"

    subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "bootstrap.py"),
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
        check=True,
    )

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

    graph = subprocess.run(
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
    payload = json.loads(graph.stdout)
    assert payload["tenant_id"] == "alpha"
    assert payload["person_count"] >= 8
    assert "Alice" in payload["people"]

    default_graph = subprocess.run(
        [
            python,
            str(repo_root / "scripts" / "graph_summary.py"),
            "--root",
            str(root),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    assert default_graph.returncode == 0, default_graph.stderr
    default_payload = json.loads(default_graph.stdout)
    assert default_payload["person_count"] == 0
