# WebUI Operator Cockpit Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real operator workflow controls to the WebUI: visible filter scope, lane-focused activity review, keyboard shortcuts, copyable inspector payloads, and interaction-state visual checks.

**Architecture:** Keep the current Vite/React single-app structure for this pass and add focused state inside `webui/src/App.tsx`. The UI remains a dense three-zone cockpit: graph workspace, activity dock, and inspector; this phase improves operability without changing backend API contracts.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, Playwright.

---

## Visual And Interaction Thesis

Visual thesis: quiet operational glass with flat controls, where state and scope are visible at a glance.

Interaction thesis:
- Filtering should leave a clear audit trail: selected scene, type, query, result counts, and one clear reset action.
- Activity review should let an operator focus one lane without losing graph context.
- Inspector payloads should be portable: copy the current node, edge, activity, or comparison as JSON.
- Keyboard shortcuts should support repeat work: focus search, clear/close, and fit graph.

## Todo

- [ ] Add a filter status bar below the ribbon with result counts, active scene/type/query chips, and a reset button.
- [ ] Add lane filter controls to the activity dock: All, Events, Patches, Snapshots.
- [ ] Add global shortcuts: `/` focuses search, `Escape` clears search or closes Inspector, `f` fits the graph viewport.
- [ ] Add an Inspector "复制 JSON" action for node, edge, activity, and compare contexts.
- [ ] Improve dense visual states: filter chips, lane tabs, copied feedback, keyboard hints that do not read like marketing copy.
- [ ] Extend visual regression to capture a desktop activity-detail state and a mobile drawer-open state.
- [ ] Verify with Vitest, production build, and Playwright visual checks.

## Files

- Modify: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`
- Modify: `webui/scripts/visual-regression.mjs`

## Task 1: Filter Scope And Reset

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [ ] Write a failing test that types a graph search, expects a status bar to show `2 / 8 nodes`, expects a `Query no-matching-node` chip for no-result states, and expects `清除过滤` to reset query/type/scene.
- [ ] Run `cd webui && npm test -- --run src/App.test.tsx` and confirm the new test fails because the filter status bar does not exist.
- [ ] Add computed filter metadata in `App.tsx`: total node count, filtered node count, active scene label, active type label, query label, and `hasActiveFilters`.
- [ ] Render `FilterStatusBar` below the control ribbon with compact chips and a reset button wired to clear scene/type/query.
- [ ] Add responsive CSS for `.filter-status`, `.filter-chip`, and `.filter-reset`.
- [ ] Re-run `cd webui && npm test -- --run src/App.test.tsx` and confirm the test passes.

## Task 2: Activity Lane Focus

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [ ] Write a failing test that clicks `Patches`, verifies only patch records are visible, then clicks `All` and verifies event records return.
- [ ] Run `cd webui && npm test -- --run src/App.test.tsx` and confirm the new test fails because lane tabs are missing.
- [ ] Add `activityLane` state in `GraphWorkspace` and pass it into `ActivityDock`.
- [ ] Render lane tabs above the lanes and hide non-selected lanes when a lane is active.
- [ ] Style tabs as compact segmented controls that preserve the existing dense activity dock.
- [ ] Re-run `cd webui && npm test -- --run src/App.test.tsx` and confirm the test passes.

## Task 3: Keyboard Shortcuts

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [ ] Write a failing test that presses `/` to focus search, types a query, presses `Escape` to clear it, clicks zoom, presses `f`, and expects zoom to return to `100%`.
- [ ] Run `cd webui && npm test -- --run src/App.test.tsx` and confirm the new test fails because shortcuts are not wired.
- [ ] Add a search input ref in `App.tsx` and a `keydown` effect for `/` and `Escape`.
- [ ] Add a `fitSignal` prop from `App` to `GraphWorkspace`; increment it when the user presses `f`.
- [ ] In `GraphWorkspace`, watch `fitSignal` and run `fitView()`.
- [ ] Add small shortcut labels inside existing controls, using restrained text that does not compete with operational labels.
- [ ] Re-run `cd webui && npm test -- --run src/App.test.tsx` and confirm the test passes.

## Task 4: Inspector Copy JSON

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [ ] Write a failing test that stubs `navigator.clipboard.writeText`, selects an activity, clicks `复制 JSON`, and verifies the copied payload includes the activity id.
- [ ] Run `cd webui && npm test -- --run src/App.test.tsx` and confirm the new test fails because copy is missing.
- [ ] Build an `inspectorPayload` object for node, edge, activity, and compare contexts.
- [ ] Add `copyInspectorPayload()` with clipboard support and a fallback to `setLastResult` when clipboard is unavailable.
- [ ] Render the action in `.inspector-actions` and show a brief `已复制` state.
- [ ] Re-run `cd webui && npm test -- --run src/App.test.tsx` and confirm the test passes.

## Task 5: Visual Regression Interaction States

**Files:**
- Modify: `webui/scripts/visual-regression.mjs`

- [ ] Extend the Playwright spec to click the first event record on desktop and save `webui-operator-cockpit-desktop-activity-detail.png`.
- [ ] Extend the mobile case to open the drawer and save `webui-operator-cockpit-mobile-drawer-open.png`.
- [ ] Keep the existing non-overflow and console-error assertions.
- [ ] Run `cd webui && npm run visual:check` and confirm all visual checks pass and screenshots are generated under `output/playwright/`.

## Final Verification

- [ ] Run `cd webui && npm test -- --run`.
- [ ] Run `cd webui && npm run build`.
- [ ] Run `cd webui && npm run visual:check`.
- [ ] Inspect the generated screenshots for obvious overlap, blank graph, hidden controls, and mobile drawer clipping.
