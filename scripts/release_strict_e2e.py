"""Strict local release/E2E gate for we-together.

This script is intentionally local-first and tokenless by default. The quick
profile exercises the product paths that must work before claiming the skill is
usable: CLI first-run, tenant isolation, MCP stdio, and WebUI local bridge curl.
The strict profile layers heavier package/Codex/test checks on top.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _step(name: str, ok: bool, detail: dict | None = None, error: str | None = None) -> dict:
    payload = {"name": name, "ok": ok}
    if detail is not None:
        payload["detail"] = detail
    if error is not None:
        payload["error"] = error
    return payload


def _run(cmd: list[str], *, cwd: Path = ROOT, env: dict | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _json_from_stdout(proc: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(proc.stdout)


def _db_counts(root: Path) -> dict:
    db = root / "db" / "main.sqlite3"
    conn = sqlite3.connect(db)
    try:
        return {
            "persons": conn.execute("SELECT COUNT(*) FROM persons WHERE status='active'").fetchone()[0],
            "relations": conn.execute("SELECT COUNT(*) FROM relations WHERE status='active'").fetchone()[0],
            "scenes": conn.execute("SELECT COUNT(*) FROM scenes WHERE status='active'").fetchone()[0],
            "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "patches": conn.execute("SELECT COUNT(*) FROM patches").fetchone()[0],
            "snapshots": conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0],
        }
    finally:
        conn.close()


def _first_active_scene(root: Path) -> str:
    conn = sqlite3.connect(root / "db" / "main.sqlite3")
    try:
        row = conn.execute(
            "SELECT scene_id FROM scenes WHERE status='active' ORDER BY scene_id LIMIT 1"
        ).fetchone()
        if row is None:
            raise RuntimeError(f"no active scene in {root}")
        return str(row[0])
    finally:
        conn.close()


def _extract_mcp_payload(resp: dict) -> dict:
    if "error" in resp:
        raise RuntimeError(json.dumps(resp["error"], ensure_ascii=False))
    result = resp.get("result") or {}
    content = result.get("content") or []
    if not content:
        raise RuntimeError(f"missing MCP content: {resp!r}")
    return json.loads(content[0]["text"])


def _call_mcp(root: Path, tool: str, arguments: dict | None = None) -> tuple[dict, dict]:
    request = {
        "jsonrpc": "2.0",
        "id": tool,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments or {}},
    }
    proc = subprocess.run(
        [PYTHON, "scripts/mcp_server.py", "--root", str(root)],
        cwd=ROOT,
        env={**os.environ, "WE_TOGETHER_LLM_PROVIDER": "mock"},
        input=json.dumps(request) + "\n",
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"MCP {tool} failed: {proc.stderr}")
    response = json.loads(proc.stdout)
    return response, _extract_mcp_payload(response)


def _http_json(url: str, *, method: str = "GET", payload: dict | None = None, timeout: float = 4.0) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
        body = json.loads(raw)
        if response.status >= 400 or body.get("ok") is False:
            raise RuntimeError(f"{method} {url} failed: {body!r}")
        return body["data"]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_http(url: str, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            _http_json(url, timeout=1.0)
            return
        except (OSError, urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"timed out waiting for {url}: {last_error}")


def _cli_first_run(root: Path) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    bootstrap = _run([PYTHON, "scripts/bootstrap.py", "--root", str(root)])
    if bootstrap.returncode != 0:
        raise RuntimeError(bootstrap.stderr)
    seed = _run([PYTHON, "scripts/seed_demo.py", "--root", str(root)])
    if seed.returncode != 0:
        raise RuntimeError(seed.stderr)
    scene_id = _first_active_scene(root)
    build_pkg = _run(
        [PYTHON, "scripts/build_retrieval_package.py", "--root", str(root), "--scene-id", scene_id]
    )
    if build_pkg.returncode != 0:
        raise RuntimeError(build_pkg.stderr)
    dialogue = _run(
        [
            PYTHON,
            "scripts/dialogue_turn.py",
            "--root",
            str(root),
            "--scene-id",
            scene_id,
            "--user-input",
            "release e2e user",
            "--response-text",
            "release e2e response",
        ]
    )
    if dialogue.returncode != 0:
        raise RuntimeError(dialogue.stderr)
    snapshot = _run([PYTHON, "scripts/snapshot.py", "--root", str(root), "list"])
    if snapshot.returncode != 0:
        raise RuntimeError(snapshot.stderr)
    counts = _db_counts(root)
    if counts["scenes"] < 1 or counts["events"] < 1 or counts["patches"] < 1 or counts["snapshots"] < 1:
        raise RuntimeError(f"insufficient CLI first-run counts: {counts}")
    return {"scene_id": scene_id, "counts": counts}


def _tenant_isolation(root: Path) -> dict:
    default_root = root / "default_case"
    alpha_base = root / "tenant_case"
    for target in (default_root, alpha_base):
        target.mkdir(parents=True, exist_ok=True)
    default_proc = _run([PYTHON, "scripts/seed_demo.py", "--root", str(default_root)])
    if default_proc.returncode != 0:
        raise RuntimeError(default_proc.stderr)
    alpha_proc = _run(
        [PYTHON, "scripts/seed_demo.py", "--root", str(alpha_base), "--tenant-id", "alpha"]
    )
    if alpha_proc.returncode != 0:
        raise RuntimeError(alpha_proc.stderr)
    default_db = default_root / "db" / "main.sqlite3"
    alpha_db = alpha_base / "tenants" / "alpha" / "db" / "main.sqlite3"
    if not default_db.exists() or not alpha_db.exists() or default_db == alpha_db:
        raise RuntimeError("tenant DB paths are not isolated")
    return {
        "default_db": str(default_db),
        "alpha_db": str(alpha_db),
        "default_counts": _db_counts(default_root),
        "alpha_counts": _db_counts(alpha_base / "tenants" / "alpha"),
    }


def _mcp_stdio(root: Path) -> dict:
    scene_id = _first_active_scene(root)
    _, self_describe = _call_mcp(root, "we_together_self_describe")
    _, graph_summary = _call_mcp(root, "we_together_graph_summary")
    _, scene_list = _call_mcp(root, "we_together_scene_list")
    snapshot_response, snapshot_list = _call_mcp(root, "we_together_snapshot_list", {"limit": 5})
    _, run_turn = _call_mcp(
        root,
        "we_together_run_turn",
        {"scene_id": scene_id, "input": "release mcp turn"},
    )
    _, import_narration = _call_mcp(
        root,
        "we_together_import_narration",
        {"scene_id": scene_id, "text": "小明和小强是朋友"},
    )
    _, proactive = _call_mcp(root, "we_together_proactive_scan", {"daily_budget": 2})
    if not run_turn.get("event_id") or not run_turn.get("snapshot_id"):
        raise RuntimeError(f"MCP run_turn missing event/snapshot: {run_turn}")
    if snapshot_list.get("tenant_id") != "default" or not snapshot_list.get("db_path"):
        raise RuntimeError(f"MCP snapshot list missing context: {snapshot_list}")
    return {
        "self_describe": {
            "version": self_describe.get("version"),
            "invariants_covered": self_describe.get("invariants_covered"),
        },
        "graph_summary": graph_summary,
        "scene_list": {"count": len(scene_list.get("scenes", []))},
        "snapshot_list": {
            "isError": (snapshot_response.get("result") or {}).get("isError", False),
            "payload": snapshot_list,
        },
        "run_turn": {"payload": run_turn},
        "import_narration": import_narration,
        "proactive_scan": proactive,
    }


def _webui_bridge_curl(root: Path) -> dict:
    port = _free_port()
    proc = subprocess.Popen(
        [
            PYTHON,
            "scripts/webui_host.py",
            "--root",
            str(root),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--provider",
            "mock",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "WE_TOGETHER_LLM_PROVIDER": "mock"},
    )
    base = f"http://127.0.0.1:{port}"
    try:
        _wait_for_http(f"{base}/api/runtime/status")
        runtime_status = _http_json(f"{base}/api/runtime/status")
        scenes = _http_json(f"{base}/api/scenes")
        if not scenes.get("scenes"):
            raise RuntimeError(f"WebUI bridge has no scenes after seed: {scenes}")
        scene_id = scenes["scenes"][0]["scene_id"]
        before_snapshots = _http_json(f"{base}/api/snapshots?limit=20")
        graph = _http_json(f"{base}/api/graph?scene_id={scene_id}")
        summary = _http_json(f"{base}/api/summary")
        world = _http_json(f"{base}/api/world?scene_id={scene_id}")
        branches = _http_json(f"{base}/api/branches?status=open")
        import_result = _http_json(
            f"{base}/api/import/narration",
            method="POST",
            payload={"text": "小王和小李是朋友"},
        )
        chat = _http_json(
            f"{base}/api/chat/run-turn",
            method="POST",
            payload={"scene_id": scene_id, "input": "release webui turn"},
        )
        events = _http_json(f"{base}/api/events?limit=20")
        patches = _http_json(f"{base}/api/patches?limit=20")
        after_snapshots = _http_json(f"{base}/api/snapshots?limit=20")
        if runtime_status.get("mode") != "local_skill" or runtime_status.get("token_required") is not False:
            raise RuntimeError(f"bad runtime status: {runtime_status}")
        if not chat.get("event_id") or not chat.get("snapshot_id"):
            raise RuntimeError(f"bad WebUI chat result: {chat}")
        return {
            "runtime_status": runtime_status,
            "scene_count": len(scenes.get("scenes", [])),
            "graph_nodes": len(graph.get("nodes", [])),
            "summary": summary,
            "world_keys": sorted(k for k in world if k != "source"),
            "branch_count": len(branches.get("branches", [])),
            "import_event_id": (import_result.get("result") or {}).get("event_id"),
            "chat": chat,
            "event_count": len(events.get("events", [])),
            "patch_count": len(patches.get("patches", [])),
            "before_chat_snapshot_count": len(before_snapshots.get("snapshots", [])),
            "after_chat_snapshot_count": len(after_snapshots.get("snapshots", [])),
        }
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()


def _package_verify(root: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / "we-together-release-e2e.weskill.zip"
    pack = _run(
        [
            PYTHON,
            "scripts/package_skill.py",
            "pack",
            "--root",
            str(ROOT),
            "--output",
            str(package_path),
        ],
        timeout=120,
    )
    if pack.returncode != 0:
        raise RuntimeError(pack.stderr)
    verify = _run(
        [PYTHON, "scripts/verify_skill_package.py", "--package", str(package_path)],
        timeout=120,
    )
    if verify.returncode != 0:
        raise RuntimeError(verify.stderr or verify.stdout)
    return {"package": str(package_path), "verify": _json_from_stdout(verify)}


def _codex_skill_validate(output_dir: Path) -> dict:
    target = output_dir / "codex-skills"
    install = _run(
        [
            PYTHON,
            "scripts/install_codex_skill.py",
            "--family",
            "--force",
            "--target-dir",
            str(target),
            "--repo-root",
            str(ROOT),
        ],
        timeout=120,
    )
    if install.returncode != 0:
        raise RuntimeError(install.stderr or install.stdout)
    config = output_dir / "codex-config.toml"
    config.write_text(
        '[mcp_servers.we-together-local-validate]\ncommand = "python3"\n',
        encoding="utf-8",
    )
    validate = _run(
        [
            PYTHON,
            "scripts/validate_codex_skill.py",
            "--family",
            "--installed",
            "--skill-dir",
            str(target),
            "--repo-root",
            str(ROOT),
            "--config-path",
            str(config),
        ],
        timeout=120,
    )
    if validate.returncode != 0:
        raise RuntimeError(validate.stderr or validate.stdout)
    return {"install": _json_from_stdout(install), "validate": _json_from_stdout(validate)}


def _run_pytest(targets: list[str]) -> dict:
    proc = _run([PYTHON, "-m", "pytest", *targets, "-q"], timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"pytest failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    return {"stdout_tail": proc.stdout.strip().splitlines()[-3:]}


def run_release_e2e(args: argparse.Namespace) -> dict:
    root = Path(args.root).resolve() if args.root else Path(tempfile.mkdtemp(prefix="wt-release-e2e-"))
    artifact_root = Path(args.artifact_root).resolve() if args.artifact_root else root / "_release_e2e_artifacts"
    steps: list[dict] = []

    def run_step(name: str, fn) -> None:
        try:
            steps.append(_step(name, True, fn()))
        except Exception as exc:
            steps.append(_step(name, False, error=str(exc)))

    run_step("cli_first_run", lambda: _cli_first_run(root))
    run_step("tenant_isolation", lambda: _tenant_isolation(root / "_tenant_matrix"))
    run_step("mcp_stdio", lambda: _mcp_stdio(root))
    run_step("webui_bridge_curl", lambda: _webui_bridge_curl(root))

    if args.require_missing_tool_for_test:
        steps.append(_step("forced_failure", False, error="forced by --require-missing-tool-for-test"))

    if not args.skip_package:
        run_step("skill_package_verify", lambda: _package_verify(root, artifact_root))

    if not args.skip_codex:
        run_step("codex_skill_family_validate", lambda: _codex_skill_validate(artifact_root))

    if args.profile == "strict":
        run_step(
            "pytest_runtime_release_focus",
            lambda: _run_pytest([
                "tests/runtime/test_mcp_server.py",
                "tests/runtime/test_webui_host.py",
                "tests/runtime/test_webui_dev.py",
                "tests/runtime/test_webui_cli.py",
                "tests/packaging/test_verify_skill_package_script.py",
                "tests/packaging/test_codex_skill_support.py",
            ]),
        )

    return {
        "ok": all(step["ok"] for step in steps),
        "profile": args.profile,
        "root": str(root),
        "artifact_root": str(artifact_root),
        "steps": steps,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run strict local release/E2E checks.")
    parser.add_argument("--profile", choices=["quick", "strict"], default="quick")
    parser.add_argument("--root", default=None)
    parser.add_argument("--artifact-root", default=None)
    parser.add_argument("--skip-package", action="store_true")
    parser.add_argument("--skip-codex", action="store_true")
    parser.add_argument(
        "--require-missing-tool-for-test",
        action="store_true",
        help="Internal regression-test knob that forces a failing step.",
    )
    args = parser.parse_args(argv)
    report = run_release_e2e(args)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=_json_default))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
