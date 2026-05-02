# WebUI Local Skill Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make WebUI chat default to the local we-together skill/CLI runtime channel instead of asking the browser user to provide a separate WebUI token.

**Architecture:** Add a local Python HTTP bridge that lives beside the existing CLI scripts and calls `we_together.services.chat_service.run_turn()` with `get_llm_client()`, inheriting the current CLI environment (`WE_TOGETHER_LLM_PROVIDER`, provider API keys, root, tenant, adapter). Vite proxies `/api/*` to that bridge during development; the React app uses the local bridge by default and keeps the token form only as an advanced remote API override. If the bridge is unavailable, the UI must say the local skill bridge is unavailable, not that the product needs a WebUI token for normal use.

**Tech Stack:** Python stdlib `http.server`, existing `we_together` services, React 19 + TypeScript + Vite proxy, Vitest Testing Library, Playwright visual regression.

---

## Product Baseline

- WebUI is a face of the local `we-together` skill runtime, not a separate SaaS-style client.
- The browser must not be the default owner of LLM provider tokens.
- Default chat turn path:
  1. Browser posts to `/api/chat/run-turn`.
  2. Local bridge receives the request on `127.0.0.1`.
  3. Bridge resolves `root` / `tenant_id`.
  4. Bridge calls `get_llm_client(provider)` and `chat_service.run_turn(...)`.
  5. Result returns to WebUI with response text, event id, snapshot id, provider, adapter, and retrieval package.
- Existing manual token remains as an advanced remote API mode, but the default label and copy must not imply that token setup is required for local skill usage.
- Event-first / reversible graph semantics stay inside `chat_service.run_turn()` and existing services. This plan does not add a new graph write path.

## File Structure

- Create: `scripts/webui_host.py`
  - Local HTTP API bridge for `/api/runtime/status` and `/api/chat/run-turn`.
  - Calls existing Python services directly.
- Create: `scripts/webui_dev.py`
  - Starts `scripts/webui_host.py` and Vite together for the default local development workflow.
- Modify: `src/we_together/cli.py`
  - Add `webui-host` and `webui` script entries.
- Modify: `webui/vite.config.ts`
  - Proxy `/api` to `WEBUI_LOCAL_BRIDGE_URL` or `http://127.0.0.1:7781`.
- Modify: `webui/package.json`
  - Make `npm run dev` start the local skill bridge launcher.
  - Add a `dev:vite` escape hatch for Vite-only development.
- Modify: `webui/src/App.tsx`
  - Treat local bridge as the default chat API path when no remote token is set.
  - Update token copy to advanced remote mode.
  - Show local bridge/provider status.
- Modify: `webui/src/App.test.tsx`
  - Add tests for default no-token chat through local bridge.
  - Add tests for bridge-unavailable fallback copy.
- Modify: `webui/scripts/visual-regression.mjs`
  - Ensure visual checks start the local bridge.
  - Assert the chat panel no longer shows the old token-required Demo message.
- Create: `tests/runtime/test_webui_host.py`
  - Unit tests for bridge status, chat turn plumbing, error handling, and no browser token requirement.

## Task 1: Local Bridge Contract Tests

**Files:**
- Create: `tests/runtime/test_webui_host.py`
- Read: `scripts/dashboard.py`
- Read: `scripts/chat.py`
- Read: `src/we_together/services/chat_service.py`

- [x] **Step 1: Write failing import and status tests**

Create `tests/runtime/test_webui_host.py` with:

```python
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "webui_host.py"


def load_webui_host():
    spec = importlib.util.spec_from_file_location("wt_webui_host", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_webui_host_script_importable():
    module = load_webui_host()
    assert hasattr(module, "build_runtime_status")
    assert hasattr(module, "run_local_chat_turn")


def test_runtime_status_uses_local_skill_mode(tmp_path):
    module = load_webui_host()
    status = module.build_runtime_status(
        root=tmp_path,
        tenant_id=None,
        provider=None,
        adapter="claude",
    )
    assert status["mode"] == "local_skill"
    assert status["provider"] == "mock"
    assert status["adapter"] == "claude"
    assert status["token_required"] is False
```

- [x] **Step 2: Run tests to verify they fail**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py -q
```

Expected: FAIL because `scripts/webui_host.py` does not exist yet.

- [x] **Step 3: Add chat turn plumbing test**

Extend `tests/runtime/test_webui_host.py` with:

```python
from types import SimpleNamespace


def test_local_chat_turn_calls_chat_service_without_browser_token(monkeypatch, tmp_path):
    module = load_webui_host()
    calls = []

    def fake_get_llm_client(provider=None):
        calls.append(("provider", provider))
        return SimpleNamespace(provider=provider or "mock")

    def fake_run_turn(**kwargs):
        calls.append(("run_turn", kwargs))
        return {
            "request": {"retrieval_package": {"scene_id": kwargs["scene_id"]}},
            "response": {"text": "local skill reply", "speaker_person_id": "skill"},
            "event_id": "evt_local",
            "snapshot_id": "snap_local",
            "applied_patch_count": 1,
        }

    monkeypatch.setattr(module, "get_llm_client", fake_get_llm_client)
    monkeypatch.setattr(module, "run_turn", fake_run_turn)

    result = module.run_local_chat_turn(
        root=tmp_path,
        tenant_id=None,
        provider=None,
        adapter="claude",
        payload={"scene_id": "scene_workroom", "input": "你好"},
    )

    assert result["mode"] == "local_skill"
    assert result["provider"] == "mock"
    assert result["text"] == "local skill reply"
    assert result["event_id"] == "evt_local"
    assert result["retrieval_package"] == {"scene_id": "scene_workroom"}
    assert calls[0] == ("provider", None)
    run_call = calls[1][1]
    assert run_call["scene_id"] == "scene_workroom"
    assert run_call["user_input"] == "你好"
    assert "token" not in run_call
```

- [x] **Step 4: Add bridge error handling tests**

Extend `tests/runtime/test_webui_host.py` with:

```python
import pytest


def test_local_chat_turn_requires_scene_and_input(tmp_path):
    module = load_webui_host()
    with pytest.raises(ValueError, match="scene_id"):
        module.run_local_chat_turn(
            root=tmp_path,
            tenant_id=None,
            provider=None,
            adapter="claude",
            payload={"input": "hello"},
        )

    with pytest.raises(ValueError, match="input"):
        module.run_local_chat_turn(
            root=tmp_path,
            tenant_id=None,
            provider=None,
            adapter="claude",
            payload={"scene_id": "scene_workroom", "input": ""},
        )
```

- [x] **Step 5: Re-run tests and keep failure focused**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py -q
```

Expected: FAIL only because `scripts/webui_host.py` is missing.

## Task 2: Implement `scripts/webui_host.py`

**Files:**
- Create: `scripts/webui_host.py`
- Test: `tests/runtime/test_webui_host.py`

- [x] **Step 1: Write the minimal bridge module**

Create `scripts/webui_host.py` with these public functions and server entrypoint:

```python
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from we_together.llm import get_llm_client
from we_together.services.chat_service import run_turn
from we_together.services.tenant_router import infer_tenant_id_from_root, resolve_tenant_root


@dataclass(frozen=True)
class BridgeConfig:
    root: Path
    tenant_id: str | None = None
    provider: str | None = None
    adapter: str = "claude"


def _json_default(value):
    if isinstance(value, Path):
        return str(value)
    return str(value)


def build_runtime_status(
    *,
    root: Path,
    tenant_id: str | None,
    provider: str | None,
    adapter: str,
) -> dict:
    tenant_root = resolve_tenant_root(Path(root).resolve(), tenant_id)
    resolved_provider = (provider or os.environ.get("WE_TOGETHER_LLM_PROVIDER") or "mock").lower().strip()
    return {
        "mode": "local_skill",
        "token_required": False,
        "provider": resolved_provider,
        "adapter": adapter,
        "tenant_id": tenant_id or infer_tenant_id_from_root(tenant_root),
        "root": str(tenant_root),
        "db_path": str(tenant_root / "db" / "main.sqlite3"),
    }


def run_local_chat_turn(
    *,
    root: Path,
    tenant_id: str | None,
    provider: str | None,
    adapter: str,
    payload: dict,
) -> dict:
    scene_id = str(payload.get("scene_id") or "").strip()
    user_input = str(payload.get("input") or "").strip()
    if not scene_id:
        raise ValueError("scene_id is required")
    if not user_input:
        raise ValueError("input is required")

    tenant_root = resolve_tenant_root(Path(root).resolve(), tenant_id)
    db_path = tenant_root / "db" / "main.sqlite3"
    llm_client = get_llm_client(provider)
    result = run_turn(
        db_path=db_path,
        scene_id=scene_id,
        user_input=user_input,
        llm_client=llm_client,
        adapter_name=adapter,
    )
    response = result.get("response") or {}
    request = result.get("request") or {}
    return {
        "mode": "local_skill",
        "provider": getattr(llm_client, "provider", provider or "unknown"),
        "adapter": adapter,
        "text": response.get("text", ""),
        "speaker_person_id": response.get("speaker_person_id"),
        "event_id": result.get("event_id"),
        "snapshot_id": result.get("snapshot_id"),
        "applied_patch_count": result.get("applied_patch_count", 0),
        "retrieval_package": request.get("retrieval_package"),
        "raw": result,
    }


def make_handler(config: BridgeConfig):
    class WebUIBridgeHandler(BaseHTTPRequestHandler):
        def _write_json(self, status: int, payload: dict):
            body = json.dumps(
                payload,
                ensure_ascii=False,
                default=_json_default,
            ).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5173")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._write_json(200, {"ok": True})

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/runtime/status":
                self._write_json(200, {
                    "ok": True,
                    "data": build_runtime_status(
                        root=config.root,
                        tenant_id=config.tenant_id,
                        provider=config.provider,
                        adapter=config.adapter,
                    ),
                })
                return
            self._write_json(404, {"ok": False, "error": {"message": "not found"}})

        def do_POST(self):
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self._write_json(400, {"ok": False, "error": {"message": str(exc)}})
                return
            if path == "/api/chat/run-turn":
                try:
                    data = run_local_chat_turn(
                        root=config.root,
                        tenant_id=config.tenant_id,
                        provider=config.provider,
                        adapter=config.adapter,
                        payload=payload,
                    )
                except Exception as exc:
                    self._write_json(500, {"ok": False, "error": {"message": str(exc)}})
                    return
                self._write_json(200, {"ok": True, "data": data})
                return
            self._write_json(404, {"ok": False, "error": {"message": "not found"}})

        def log_message(self, *args, **kwargs):
            pass

    return WebUIBridgeHandler


def main() -> int:
    parser = argparse.ArgumentParser(description="Local WebUI bridge for the we-together skill runtime")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--adapter", default="claude", choices=["claude", "openai", "openai_compat"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7781)
    args = parser.parse_args()
    config = BridgeConfig(
        root=Path(args.root).resolve(),
        tenant_id=args.tenant_id,
        provider=args.provider,
        adapter=args.adapter,
    )
    server = HTTPServer((args.host, args.port), make_handler(config))
    print(f"we-together WebUI bridge: http://{args.host}:{args.port} provider={build_runtime_status(root=config.root, tenant_id=config.tenant_id, provider=config.provider, adapter=config.adapter)['provider']}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 2: Run bridge unit tests**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py -q
```

Expected: PASS.

- [x] **Step 3: Run existing chat service tests**

Run:

```bash
.venv/bin/python -m pytest tests/services/test_chat_service.py tests/runtime/test_mcp_server.py -q
```

Expected: PASS, confirming the bridge did not bypass existing skill runtime behavior.

## Task 3: CLI And Dev Launch Defaults

**Files:**
- Modify: `src/we_together/cli.py`
- Create: `scripts/webui_dev.py`
- Modify: `webui/package.json`
- Test: `tests/runtime/test_webui_host.py`

- [x] **Step 1: Add failing CLI map test**

Extend `tests/runtime/test_webui_host.py` with:

```python
def test_cli_exposes_webui_host_and_webui_launcher():
    from we_together.cli import SCRIPT_MAP

    assert SCRIPT_MAP["webui-host"] == "webui_host.py"
    assert SCRIPT_MAP["webui"] == "webui_dev.py"
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py::test_cli_exposes_webui_host_and_webui_launcher -q
```

Expected: FAIL because CLI subcommands do not exist yet.

- [x] **Step 3: Add CLI script map entries**

Modify `src/we_together/cli.py`:

```python
SCRIPT_MAP = {
    ...
    "chat": "chat.py",
    "webui-host": "webui_host.py",
    "webui": "webui_dev.py",
    # Phase 18+
    ...
}
```

- [x] **Step 4: Add local dev launcher**

Create `scripts/webui_dev.py`:

```python
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WebUI with the local we-together skill bridge")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--tenant-id", default=None)
    parser.add_argument("--provider", default=None)
    parser.add_argument("--adapter", default="claude")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--api-port", type=int, default=7781)
    args = parser.parse_args()

    bridge_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "webui_host.py"),
        "--root",
        str(Path(args.root).resolve()),
        "--host",
        args.host,
        "--port",
        str(args.api_port),
        "--adapter",
        args.adapter,
    ]
    if args.tenant_id:
        bridge_cmd.extend(["--tenant-id", args.tenant_id])
    if args.provider:
        bridge_cmd.extend(["--provider", args.provider])

    env = {
        **os.environ,
        "WEBUI_LOCAL_BRIDGE_URL": f"http://{args.host}:{args.api_port}",
    }
    bridge = subprocess.Popen(bridge_cmd, cwd=ROOT, env=env)
    vite = subprocess.Popen(
        ["npx", "vite", "--host", args.host, "--port", str(args.port)],
        cwd=ROOT / "webui",
        env=env,
    )
    children = [bridge, vite]

    def stop_children(*_args):
        for child in children:
            if child.poll() is None:
                child.terminate()

    signal.signal(signal.SIGINT, stop_children)
    signal.signal(signal.SIGTERM, stop_children)
    try:
        while True:
            for child in children:
                code = child.poll()
                if code is not None:
                    stop_children()
                    return code
            signal.pause()
    finally:
        stop_children()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [x] **Step 5: Make npm dev run the skill bridge by default**

Modify `webui/package.json` scripts:

```json
{
  "scripts": {
    "dev": "python3 ../scripts/webui_dev.py --root ..",
    "dev:vite": "vite --host 127.0.0.1",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview --host 127.0.0.1",
    "test": "vitest --environment jsdom src",
    "visual:check": "node scripts/visual-regression.mjs"
  }
}
```

- [x] **Step 6: Run CLI tests**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py::test_cli_exposes_webui_host_and_webui_launcher -q
```

Expected: PASS.

## Task 4: Vite Proxy To Local Bridge

**Files:**
- Modify: `webui/vite.config.ts`
- Test: `webui/src/App.test.tsx`

- [x] **Step 1: Modify Vite config**

Update `webui/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const localBridgeUrl = process.env.WEBUI_LOCAL_BRIDGE_URL || "http://127.0.0.1:7781";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: localBridgeUrl,
        changeOrigin: true
      }
    }
  },
  preview: {
    port: 4173
  }
});
```

- [x] **Step 2: Run WebUI build**

Run:

```bash
cd webui && npm run build
```

Expected: PASS.

## Task 5: React Default Local Skill Channel

**Files:**
- Modify: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`

- [x] **Step 1: Write failing frontend test for default no-token chat**

Add to `webui/src/App.test.tsx`:

```tsx
it("runs chat turns through the local skill bridge by default without a WebUI token", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
    ok: true,
    json: async () => ({
      ok: true,
      data: {
        mode: "local_skill",
        provider: "mock",
        adapter: "claude",
        text: "local skill reply",
        event_id: "evt_local",
        retrieval_package: { scene_id: "scene_workroom" }
      }
    })
  } as Response);

  render(<App />);

  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: /^对话$/i }));
  await user.type(screen.getByLabelText(/Scene-grounded input/i), "你好");
  await user.click(screen.getByRole("button", { name: /运行 turn/i }));

  await waitFor(() => {
    expect(screen.getByText(/local skill reply/i)).toBeInTheDocument();
  });
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/chat/run-turn",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ scene_id: "scene_workroom", input: "你好" })
    })
  );
  const [, init] = fetchMock.mock.calls[0];
  expect(JSON.stringify(init?.headers || {})).not.toContain("Authorization");
});
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
cd webui && npm test -- --run src/App.test.tsx
```

Expected: FAIL because the no-token path still emits the old Demo message and does not call `/api/chat/run-turn`.

- [x] **Step 3: Write failing fallback-copy test**

Add to `webui/src/App.test.tsx`:

```tsx
it("explains local bridge availability instead of asking for a token when the default chat channel is down", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("bridge offline"));
  render(<App />);

  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: /^对话$/i }));
  await user.type(screen.getByLabelText(/Scene-grounded input/i), "你好");
  await user.click(screen.getByRole("button", { name: /运行 turn/i }));

  await waitFor(() => {
    expect(screen.getByText(/Local skill bridge unavailable/i)).toBeInTheDocument();
  });
  expect(screen.queryByText(/连接 WebUI token 后会调用真实/i)).not.toBeInTheDocument();
});
```

- [x] **Step 4: Implement optional-token API client**

Modify `ApiClient` in `webui/src/App.tsx` so token is optional:

```ts
class ApiClient {
  token?: string;

  constructor(token?: string) {
    this.token = token || undefined;
  }

  async request<T>(url: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((init.headers as Record<string, string> | undefined) || {})
    };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    const response = await fetch(url, {
      ...init,
      headers
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload?.error?.message || response.statusText || `HTTP ${response.status}`);
    }
    return payload.data;
  }
}
```

- [x] **Step 5: Route no-token chat through local bridge**

Modify `runTurn` in `webui/src/App.tsx`:

```ts
async function runTurn(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  if (!chatInput.trim()) return;
  const activeScene = sceneId || data.scenes[0]?.scene_id;
  if (!activeScene) {
    setError("需要至少一个 scene 才能运行对话。");
    return;
  }
  const chatClient = client || new ApiClient();
  try {
    const result = await chatClient.request<Record<string, unknown>>("/api/chat/run-turn", {
      method: "POST",
      body: JSON.stringify({ scene_id: activeScene, input: chatInput })
    });
    setChatOutput(`${asText(result.text)}\n\n事件：${asText(result.event_id)}\n通道：${asText(result.mode || "remote_api")} · ${asText(result.provider || "unknown")}`);
    setRetrievalPackage((result.retrieval_package as Record<string, unknown>) || null);
    setChatInput("");
    if (client) await loadData();
  } catch (err) {
    const reason = err instanceof Error ? err.message : String(err);
    setChatOutput(`Local skill bridge unavailable: ${reason}\n\n请通过 we-together webui 或 npm run dev 启动本地 bridge；远程 token 只用于高级部署模式。`);
    setRetrievalPackage({ mode: "local_skill_unavailable", scene_id: activeScene, reason });
  }
}
```

- [x] **Step 6: Update token UI copy**

Modify the token form labels in `webui/src/App.tsx`:

```tsx
<span>Remote API token</span>
...
placeholder={token ? "远程 API 已连接" : "可选高级模式"}
```

Keep the local status pill copy aligned with local-first semantics:

```tsx
{client ? "Remote API" : "Local skill bridge"}
```

- [x] **Step 7: Run focused WebUI tests**

Run:

```bash
cd webui && npm test -- --run src/App.test.tsx
```

Expected: PASS.

## Task 6: Visual Regression And Full Verification

**Files:**
- Modify: `webui/scripts/visual-regression.mjs`
- Modify: `docs/superpowers/plans/2026-04-29-webui-local-skill-bridge.md`

- [x] **Step 1: Update visual regression startup**

Modify `webui/scripts/visual-regression.mjs` so visual checks start the bridge before Vite:

```js
const apiPort = Number(process.env.WEBUI_VISUAL_API_PORT || 7781);
const bridgeUrl = process.env.WEBUI_LOCAL_BRIDGE_URL || `http://127.0.0.1:${apiPort}`;
```

When starting Vite, pass:

```js
env: {
  ...process.env,
  WEBUI_LOCAL_BRIDGE_URL: bridgeUrl
}
```

Start the Python bridge if `bridgeUrl` is not reachable:

```js
let bridge = null;
if (!(await isReachable(`${bridgeUrl}/api/runtime/status`))) {
  bridge = spawn("python3", ["../scripts/webui_host.py", "--root", "..", "--port", String(apiPort)], {
    cwd: root,
    env: process.env,
    stdio: "inherit"
  });
  await waitForServer(`${bridgeUrl}/api/runtime/status`);
}
```

Kill `bridge` in the existing `finally` block.

- [x] **Step 2: Add visual assertion for local-first chat copy**

Inside the desktop visual case, add:

```js
await page.getByRole("button", { name: /^对话$/ }).click();
await expect(page.getByText(/Local skill bridge|local_skill/i)).toBeVisible();
await expect(page.getByText(/连接 WebUI token 后会调用真实/)).toHaveCount(0);
```

- [x] **Step 3: Run full frontend verification**

Run:

```bash
cd webui && npm test -- --run
cd webui && npm run build
cd webui && npm run visual:check
```

Expected:

- Vitest: all WebUI tests pass.
- Build: `tsc --noEmit && vite build` passes.
- Visual: desktop and mobile checks pass.

- [x] **Step 4: Run backend bridge verification**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py tests/services/test_chat_service.py tests/runtime/test_mcp_server.py -q
```

Expected: PASS.

- [x] **Step 5: Manual smoke command**

Run:

```bash
.venv/bin/python scripts/webui_host.py --root . --port 7781
```

In another terminal:

```bash
curl -s http://127.0.0.1:7781/api/runtime/status
curl -s -X POST http://127.0.0.1:7781/api/chat/run-turn \
  -H 'Content-Type: application/json' \
  -d '{"scene_id":"scene_workroom","input":"你好"}'
```

Expected:

- Status JSON includes `"mode": "local_skill"` and `"token_required": false`.
- Chat JSON returns `ok: true` when the local DB has `scene_workroom`.
- If the DB/scene is unavailable, the JSON error names the missing scene or DB condition without asking for a browser token.

## Self-Review Checklist

- [x] **Spec coverage:** Covers local skill-first default, no browser token default, CLI/provider inheritance, remote-token advanced path, and unavailable-bridge fallback.
- [x] **No placeholder scan:** Plan contains no unfinished marker phrases or unspecified error-handling steps.
- [x] **Type consistency:** Planned bridge returns `mode`, `provider`, `adapter`, `text`, `event_id`, and `retrieval_package`; frontend tests and implementation use the same property names.
- [x] **Invariant check:** All graph writes remain inside `chat_service.run_turn()`, preserving event-first and reversible write semantics.
- [x] **Scope check:** This plan is limited to WebUI local chat channel productionization. It does not attempt to replace the existing graph/review API surface.

## Post-Review Hardening

- [x] `scripts/webui_dev.py` readiness now validates `/api/runtime/status` JSON and requires `data.mode == "local_skill"` before starting Vite.
- [x] WebUI now reads `/api/runtime/status` and shows actual local provider/adapter status for the default channel.
- [x] Remote token mode now reports remote API failures separately instead of mislabeling them as local bridge outages.
- [x] Metrics copy now uses `Local runtime` instead of `Demo-ready`.
- [x] Added regression tests for bridge identity validation, runtime status display, remote error copy, and local-runtime metrics wording.
