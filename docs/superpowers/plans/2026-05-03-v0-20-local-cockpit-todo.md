# v0.20 Local Cockpit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 WebUI 从半 demo cockpit 推进到默认连接当前 CLI / skill runtime 的本地产品化工作台。

**Architecture:** 浏览器默认不持有 provider token，只请求 `scripts/webui_host.py` 的本地 bridge；bridge 在当前 CLI 环境内读取 tenant SQLite、调用 importer/chat/patch/world 服务。Remote API token 只保留为高级部署模式。

**Tech Stack:** Python HTTP bridge + SQLite services + React/Vite/Vitest + Playwright visual smoke + curl E2E.

---

## Visual Thesis

WebUI 保持克制的 operational cockpit：Liquid glass 只作为材质层，真实图谱、活动流、复核队列和导入动作才是视觉主角。

## Content Plan

第一屏继续以图谱工作台为主；空 runtime 时给出一键 bootstrap/seed/import；对话、world、review、metrics 都读取真实 local bridge 数据；不再用 demo 数据伪装本地运行态。

## Interaction Thesis

本地 bridge 在线时所有主操作都走当前 skill runtime；空库初始化是一个显式 operator action；复核决策必须二次确认后才调用 branch resolve。

## File Boundaries

- Modify: `scripts/webui_host.py`
  - 新增 `/api/graph`、`/api/events`、`/api/patches`、`/api/snapshots`、`/api/branches`、`/api/world` 只读接口。
  - 新增 `/api/bootstrap`、`/api/seed-demo`、`/api/import/narration`、`/api/branches/<branch_id>/resolve` 写接口。
  - 保持 `/api/chat/run-turn` 继续通过 `chat_service.run_turn()` 使用当前 CLI provider 环境。
- Modify: `tests/runtime/test_webui_host.py`
  - 用最小 SQLite schema 锁定 graph/activity/world/import/bootstrap/seed/branch resolve 行为。
- Modify: `webui/src/App.tsx`
  - no-token 模式加载真实 bridge API，bridge 离线时才降级 demo。
  - 增加空 runtime 初始化与 narration import 控件。
  - local review resolve 走 `/api/branches/<id>/resolve`，不再 demo-only。
- Modify: `webui/src/App.test.tsx`
  - 覆盖 no-token 真实数据读取、seed/import action、local branch resolve 不带 Authorization。
- Modify: `webui/src/styles.css`
  - 给本地 action 面板和导入 composer 做扁平/玻璃两主题兼容样式。
- Modify: `docs/wiki/architecture.md`, `docs/wiki/usage.md`, `docs/wiki/interaction-flows.md`
  - 补 v0.20 local cockpit 架构、使用方式与交互流程。
- Modify: `docs/HANDOFF.md`, `docs/superpowers/state/current-status.md`
  - 更新当前进展和下一节点事实。

---

## Task 1: Backend Bridge Read APIs

- [x] **Step 1: Write failing tests**
  - Add tests for `build_local_graph()`, `list_local_events()`, `list_local_patches()`, `list_local_snapshots()`, `list_local_branches()`, and `build_local_world()`.
  - Expected behavior:
    - graph returns real person/memory/group/scene nodes and scene/entity/memory/group edges.
    - activity endpoints return recent records from SQLite and tolerate missing tables.
    - branch endpoint returns open branches with candidates and decoded `payload_json`.
    - world endpoint returns empty arrays if world tables are absent and real rows if present.

- [x] **Step 2: Verify RED**
  - Run: `.venv/bin/python -m pytest tests/runtime/test_webui_host.py -q`
  - Expected: failures for missing backend helper functions/routes.

- [x] **Step 3: Implement minimal read APIs**
  - Add safe table/column helpers and JSON decoding in `scripts/webui_host.py`.
  - Add GET routes for graph/events/patches/snapshots/branches/world.

- [x] **Step 4: Verify GREEN**
  - Run: `.venv/bin/python -m pytest tests/runtime/test_webui_host.py -q`
  - Expected: focused host tests pass.

## Task 2: Backend Bridge Write APIs

- [x] **Step 1: Write failing tests**
  - Add tests for:
    - `bootstrap_local_runtime()` calling `bootstrap_project()`.
    - `seed_local_demo()` calling `seed_society_c()`.
    - `import_local_narration()` validating text and returning ingestion result.
    - `resolve_local_branch()` building and applying a `resolve_local_branch` patch.

- [x] **Step 2: Verify RED**
  - Run: `.venv/bin/python -m pytest tests/runtime/test_webui_host.py -q`
  - Expected: failures for missing write helpers/routes.

- [x] **Step 3: Implement write APIs**
  - Wire POST `/api/bootstrap`, `/api/seed-demo`, `/api/import/narration`, `/api/branches/<branch_id>/resolve`.
  - Bootstrap before seed/import when needed.
  - Preserve token-free local bridge semantics.

- [x] **Step 4: Verify GREEN**
  - Run: `.venv/bin/python -m pytest tests/runtime/test_webui_host.py -q`
  - Expected: focused host tests pass.

## Task 3: Frontend Local Runtime Data Flow

- [x] **Step 1: Write failing tests**
  - Add Vitest coverage proving no-token `loadData()` fetches `/api/graph`, `/api/events`, `/api/patches`, `/api/snapshots`, `/api/world`, `/api/branches`.
  - Assert real local node/branch/world/activity values render and demo graph values are not used when bridge succeeds.

- [x] **Step 2: Verify RED**
  - Run: `cd webui && npm test -- --run src/App.test.tsx`
  - Expected: failures because no-token path currently only fetches summary/scenes.

- [x] **Step 3: Implement local data flow**
  - Update no-token load path to call all bridge APIs in parallel.
  - Use demo data only when bridge is offline.
  - Refresh data after successful local chat turn.

- [x] **Step 4: Verify GREEN**
  - Run: `cd webui && npm test -- --run src/App.test.tsx`
  - Expected: App tests pass.

## Task 4: Frontend Runtime Actions

- [x] **Step 1: Write failing tests**
  - Add tests for one-click seed-demo, narration import, and local branch resolve POST.
  - Assert no Authorization header is sent in local mode.

- [x] **Step 2: Verify RED**
  - Run: `cd webui && npm test -- --run src/App.test.tsx`
  - Expected: failures because controls and local resolve action are missing.

- [x] **Step 3: Implement runtime actions**
  - Add operator action strip for bootstrap/seed/import.
  - Add narration textarea/button in chat panel.
  - Change local review resolve to call bridge route, then reload.

- [x] **Step 4: Verify GREEN**
  - Run: `cd webui && npm test -- --run src/App.test.tsx`
  - Expected: App tests pass.

## Task 5: Docs And State

- [x] **Step 1: Update wiki**
  - `docs/wiki/architecture.md`: document browser -> local bridge -> skill runtime -> SQLite flow.
  - `docs/wiki/usage.md`: document `we-together webui`, local no-token default, optional remote token.
  - `docs/wiki/interaction-flows.md`: document bootstrap/seed/import/chat/review flows.

- [x] **Step 2: Update handoff/status**
  - Record v0.20 local cockpit progress in `docs/HANDOFF.md` and `docs/superpowers/state/current-status.md`.

- [x] **Step 3: Verify docs**
  - Run existing link/stale scans if available and include output in final evidence.

## Task 6: End-to-End Verification

- [x] **Step 1: Backend regression**
  - Run: `.venv/bin/python -m pytest tests/runtime/test_webui_host.py tests/runtime/test_webui_dev.py tests/runtime/test_webui_cli.py tests/services/test_chat_service.py tests/runtime/test_mcp_server.py -q`

- [x] **Step 2: Frontend regression**
  - Run: `cd webui && npm test -- --run`
  - Run: `cd webui && npm run build`
  - Run: `cd webui && npm run visual:check`

- [x] **Step 3: Curl E2E**
  - Start bridge on a temp root and non-default port.
  - Curl bootstrap, seed-demo, graph, activity, world, import narration, chat run-turn, branch list.
  - Verify the bridge returns real local skill data and chat/import writes event/patch/snapshot rows.

- [x] **Step 4: Final self-audit**
  - Re-read this plan and mark completed checkboxes.
  - Run `git diff --stat` and summarize only files touched by this phase.
