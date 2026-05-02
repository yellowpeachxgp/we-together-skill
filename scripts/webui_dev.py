"""Start the WebUI local skill bridge and Vite dev server together.

The WebUI is a local face of the we-together skill runtime. This launcher keeps
the browser on a tokenless default path by starting `scripts/webui_host.py` and
then proxying Vite `/api/*` requests to that local bridge.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _has_vite_port_arg(args: list[str]) -> bool:
    return any(arg == "--port" or arg.startswith("--port=") for arg in args)


def _wait_for_bridge(url: str, timeout_seconds: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and payload.get("ok") is True and payload.get("data", {}).get("mode") == "local_skill":
                    return
                last_error = RuntimeError(f"unexpected bridge status payload: {payload!r}")
        except (OSError, urllib.error.URLError) as exc:
            last_error = exc
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError) as exc:
            last_error = exc
        time.sleep(0.2)
    detail = f": {last_error}" if last_error else ""
    raise RuntimeError(f"Timed out waiting for local WebUI bridge at {url}{detail}")


def _terminate(child: subprocess.Popen[str] | None) -> None:
    if child is None or child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=4)
    except subprocess.TimeoutExpired:
        child.kill()


def _build_commands(
    *,
    runtime_root: Path,
    repo_root: Path,
    tenant_id: str | None,
    provider: str | None,
    adapter: str,
    bridge_host: str,
    bridge_port: int,
    vite_host: str,
    vite_port: int,
    vite_args: list[str],
) -> tuple[list[str], list[str], dict[str, Path]]:
    runtime_root = Path(runtime_root).resolve()
    repo_root = Path(repo_root).resolve()
    bridge_url = f"http://{bridge_host}:{bridge_port}"
    bridge_script = repo_root / "scripts" / "webui_host.py"
    webui_root = repo_root / "webui"

    bridge_cmd = [
        sys.executable,
        str(bridge_script),
        "--root",
        str(runtime_root),
        "--host",
        bridge_host,
        "--port",
        str(bridge_port),
        "--adapter",
        adapter,
    ]
    if tenant_id:
        bridge_cmd.extend(["--tenant-id", tenant_id])
    if provider:
        bridge_cmd.extend(["--provider", provider])

    vite_cmd = ["npm", "run", "dev:vite", "--", "--host", vite_host]
    if not _has_vite_port_arg(vite_args):
        vite_cmd.extend(["--port", str(vite_port)])
    vite_cmd.extend(vite_args)

    return bridge_cmd, vite_cmd, {
        "bridge": repo_root,
        "vite": webui_root,
        "runtime_root": runtime_root,
        "repo_root": repo_root,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run WebUI with the local we-together skill bridge.",
        allow_abbrev=False,
    )
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--adapter", default="claude", choices=["claude", "openai", "openai_compat"])
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=int(os.environ.get("WEBUI_LOCAL_BRIDGE_PORT", "7781")))
    parser.add_argument("--vite-host", default="127.0.0.1")
    parser.add_argument("--vite-port", type=int, default=int(os.environ.get("WEBUI_VISUAL_PORT", "5173")))
    args, vite_args = parser.parse_known_args(argv)

    runtime_root = Path(args.root).resolve()
    repo_root = ROOT.resolve()
    bridge_url = f"http://{args.bridge_host}:{args.bridge_port}"
    bridge_cmd, vite_cmd, cwd_map = _build_commands(
        runtime_root=runtime_root,
        repo_root=repo_root,
        tenant_id=args.tenant_id,
        provider=args.provider,
        adapter=args.adapter,
        bridge_host=args.bridge_host,
        bridge_port=args.bridge_port,
        vite_host=args.vite_host,
        vite_port=args.vite_port,
        vite_args=vite_args,
    )

    env = {**os.environ, "WEBUI_LOCAL_BRIDGE_URL": bridge_url}
    bridge: subprocess.Popen[str] | None = None
    vite: subprocess.Popen[str] | None = None

    def stop_children(_signum=None, _frame=None) -> None:
        _terminate(vite)
        _terminate(bridge)

    signal.signal(signal.SIGTERM, stop_children)
    signal.signal(signal.SIGINT, stop_children)

    try:
        bridge = subprocess.Popen(bridge_cmd, cwd=str(cwd_map["bridge"]), env=env)
        _wait_for_bridge(f"{bridge_url}/api/runtime/status")
        vite = subprocess.Popen(vite_cmd, cwd=str(cwd_map["vite"]), env=env)
        return vite.wait()
    finally:
        stop_children()


if __name__ == "__main__":
    raise SystemExit(main())
