from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "release_strict_e2e.py"


def _run_release_e2e(*args: str, timeout: int = 180) -> tuple[int, dict, str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"release_strict_e2e.py did not emit JSON\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        ) from exc
    return proc.returncode, payload, proc.stderr


def test_release_strict_e2e_quick_profile_covers_local_runtime(tmp_path):
    code, report, stderr = _run_release_e2e(
        "--profile",
        "quick",
        "--root",
        str(tmp_path / "runtime"),
        "--skip-package",
        "--skip-codex",
    )

    assert code == 0, stderr
    assert report["ok"] is True
    steps = {step["name"]: step for step in report["steps"]}
    for required in [
        "cli_first_run",
        "tenant_isolation",
        "mcp_stdio",
        "webui_bridge_curl",
    ]:
        assert steps[required]["ok"] is True

    mcp = steps["mcp_stdio"]["detail"]
    assert mcp["snapshot_list"]["isError"] is False
    assert mcp["run_turn"]["payload"]["event_id"].startswith("evt_")
    assert mcp["run_turn"]["payload"]["snapshot_id"].startswith("snap_")

    webui = steps["webui_bridge_curl"]["detail"]
    assert webui["runtime_status"]["token_required"] is False
    assert webui["chat"]["event_id"].startswith("evt_")
    assert webui["after_chat_snapshot_count"] >= webui["before_chat_snapshot_count"]


def test_release_strict_e2e_reports_failed_step_with_nonzero_exit(tmp_path):
    code, report, _stderr = _run_release_e2e(
        "--profile",
        "quick",
        "--root",
        str(tmp_path / "runtime"),
        "--require-missing-tool-for-test",
    )

    assert code != 0
    assert report["ok"] is False
    failing = [step for step in report["steps"] if not step["ok"]]
    assert any(step["name"] == "forced_failure" for step in failing)
