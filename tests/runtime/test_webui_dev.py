from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "webui_dev.py"


def load_webui_dev():
    spec = importlib.util.spec_from_file_location("wt_webui_dev", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status: int, body: bytes):
        self.status = status
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body


def test_wait_for_bridge_requires_local_skill_status(monkeypatch):
    module = load_webui_dev()
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        module.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(200, b'{"ok": true, "data": {"mode": "not_we_together"}}'),
    )

    with pytest.raises(RuntimeError, match="local WebUI bridge"):
        module._wait_for_bridge("http://127.0.0.1:7781/api/runtime/status", timeout_seconds=0.001)


def test_wait_for_bridge_accepts_local_skill_status(monkeypatch):
    module = load_webui_dev()
    monkeypatch.setattr(
        module.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(200, b'{"ok": true, "data": {"mode": "local_skill"}}'),
    )

    module._wait_for_bridge("http://127.0.0.1:7781/api/runtime/status", timeout_seconds=0.001)


def test_build_commands_keep_repo_root_separate_from_runtime_root(tmp_path):
    module = load_webui_dev()
    runtime_root = tmp_path / "data"

    bridge_cmd, vite_cmd, cwd_map = module._build_commands(
        runtime_root=runtime_root,
        repo_root=REPO_ROOT,
        tenant_id="alpha",
        provider="mock",
        adapter="claude",
        bridge_host="127.0.0.1",
        bridge_port=7789,
        vite_host="127.0.0.1",
        vite_port=5199,
        vite_args=[],
    )

    assert str(REPO_ROOT / "scripts" / "webui_host.py") in bridge_cmd
    root_index = bridge_cmd.index("--root") + 1
    assert bridge_cmd[root_index] == str(runtime_root.resolve())
    assert "--tenant-id" in bridge_cmd
    assert "alpha" in bridge_cmd
    assert cwd_map["bridge"] == REPO_ROOT
    assert cwd_map["vite"] == REPO_ROOT / "webui"
    assert vite_cmd[:3] == ["npm", "run", "dev:vite"]
