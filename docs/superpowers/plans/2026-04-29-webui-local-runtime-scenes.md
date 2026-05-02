# WebUI Local Runtime Scenes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make no-token WebUI chat choose scenes from the local skill bridge instead of static demo scene ids.

**Architecture:** Extend `scripts/webui_host.py` with read-only `/api/scenes` and `/api/summary` endpoints backed by the resolved tenant SQLite database. Update `webui/src/App.tsx` so no-token mode fetches those local runtime endpoints and merges them into the existing visual demo fallback, allowing chat turns to target real local scenes while keeping the UI usable for empty/offline runtimes. All graph writes remain inside `chat_service.run_turn()`.

**Tech Stack:** Python stdlib `sqlite3` + `http.server`, React 19 + TypeScript, Vitest Testing Library, curl smoke checks.

---

## Product Baseline

- WebUI default mode is local skill runtime, not static SaaS demo mode.
- Browser still does not own provider tokens.
- No-token chat default scene must come from `/api/scenes` when the local bridge is reachable.
- Empty local DBs must surface a local runtime initialization hint instead of silently sending `scene_workroom`.
- Static demo graph remains a visual fallback until the bridge grows full graph/review endpoints.

## Task 1: Backend Local Runtime Read Endpoints

**Files:**
- Modify: `scripts/webui_host.py`
- Modify: `tests/runtime/test_webui_host.py`

- [x] **Step 1: Add failing unit tests**

Add tests for `list_local_scenes()` and `build_local_summary()` using a tiny SQLite database with `scenes`, `persons`, `relations`, `memories`, `events`, `patches`, `snapshots`, and `local_branches`.

- [x] **Step 2: Run red test**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py -q
```

Expected: FAIL because the helper functions do not exist.

- [x] **Step 3: Implement read-only helpers and GET routes**

Implement:

- `list_local_scenes(root, tenant_id)` -> `{"scenes": [...], "source": "local_skill"}`
- `build_local_summary(root, tenant_id)` -> summary counts and `db_exists`
- `GET /api/scenes`
- `GET /api/summary`

- [x] **Step 4: Run backend tests**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py tests/runtime/test_webui_dev.py tests/runtime/test_webui_cli.py -q
```

Expected: PASS.

## Task 2: Frontend Local Scene Binding

**Files:**
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/App.test.tsx`

- [x] **Step 1: Add failing frontend tests**

Add tests proving:

- No-token load fetches `/api/summary` and `/api/scenes`.
- Chat default scene uses the first local bridge scene id.
- Empty local scene list produces a local runtime initialization hint and does not call `/api/chat/run-turn`.

- [x] **Step 2: Run red test**

Run:

```bash
cd webui && npm test -- --run src/App.test.tsx
```

Expected: FAIL because no-token `loadData()` still uses `demoData`.

- [x] **Step 3: Implement no-token local data load**

In `loadData()`:

- When no remote token client exists, create `new ApiClient()`.
- Fetch `/api/summary` and `/api/scenes`.
- Merge the returned summary/scenes into `demoData` so graph visuals remain available.
- Preserve fallback to `demoData` when bridge is offline.

In `runTurn()`:

- Use `data.scenes[0]?.scene_id` for default scene.
- If no local scenes exist, show `Local runtime has no scenes yet...` with bootstrap/seed/import guidance.

- [x] **Step 4: Run frontend tests**

Run:

```bash
cd webui && npm test -- --run src/App.test.tsx
```

Expected: PASS.

## Task 3: Verification And Curl Smoke

**Files:**
- Modify: `docs/superpowers/plans/2026-04-29-webui-local-runtime-scenes.md`

- [x] **Step 1: Run full verification**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_webui_host.py tests/runtime/test_webui_dev.py tests/runtime/test_webui_cli.py tests/services/test_chat_service.py tests/runtime/test_mcp_server.py -q
cd webui && npm test -- --run
cd webui && npm run build
cd webui && npm run visual:check
```

Expected: all commands pass.

- [x] **Step 2: Curl current local runtime**

Run:

```bash
curl -s http://127.0.0.1:5173/api/runtime/status
curl -s http://127.0.0.1:5173/api/scenes
curl -s http://127.0.0.1:5173/api/summary
```

Expected: status is `local_skill`, token is not required, scenes reflect the current DB rather than static demo data.

- [x] **Step 3: Curl seeded isolated runtime**

Create a temp root with `bootstrap.py` and `seed_demo.py`, run bridge + Vite proxy against it, then POST `/api/chat/run-turn` without Authorization.

Expected: chat returns `ok: true`, a real `event_id`, a real `snapshot_id`, and a patch count. SQLite confirms the event, snapshot, and patch exist.

## Self-Review Checklist

- [x] **Spec coverage:** Covers real local scene loading, empty runtime behavior, bridge read endpoints, and curl verification.
- [x] **No placeholder scan:** All tasks name exact files, commands, and expected outcomes.
- [x] **Invariant check:** Adds only read endpoints plus the existing `chat_service.run_turn()` write path.
- [x] **Scope check:** Does not attempt full graph/review API replacement in this slice.
