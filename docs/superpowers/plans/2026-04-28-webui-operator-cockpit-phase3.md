# WebUI Operator Cockpit Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the Operator Cockpit TODO stream by adding a fast command palette, a more serious operator review queue, and a scannable runtime telemetry page.

**Architecture:** Keep the current single React app shape for this pass. Add a small command model in `App.tsx`, upgrade `ReviewPanel` and `MetricsPanel` in place, and keep visual regression coverage in the existing Playwright script.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, Playwright.

---

## Visual And Interaction Thesis

Visual thesis: an operator cockpit should feel fast, inspectable, and low-noise; the UI should make the next action visible without adding decorative weight.

Interaction thesis:
- Operators need a fast command layer for jumping to nodes and views without scanning the whole page.
- Review should look like a triage queue, not a loose list of buttons.
- Metrics should be a compact telemetry surface with bars and health rows instead of isolated stat cards.

## Todo

- [x] Add a command palette opened by `Ctrl/Meta+K` and a visible command button.
- [x] Let the command palette search views and graph nodes, then jump/select without losing Inspector context.
- [x] Upgrade Review into a queue with branch totals, candidate totals, selected candidate preview, and operator note.
- [x] Upgrade Metrics into runtime telemetry with graph load, event flow, branch pressure, patch health, and API mode rows.
- [x] Extend visual regression with command-palette, review-queue, and telemetry screenshots.
- [x] Verify with Vitest, production build, Playwright visual checks, and screenshot inspection.

## Task 1: Command Palette

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [x] Write failing tests for `Ctrl+K` opening `命令面板`, selecting `Carol person`, and jumping to `Operator Review`.
- [x] Run `cd webui && npm test -- --run src/App.test.tsx` and confirm the tests fail because the palette is missing.
- [x] Add command state, command query, command model, and activation handlers in `App.tsx`.
- [x] Render a modal command palette with search, grouped result rows, keyboard-safe Escape behavior, and a visible topbar command button.
- [x] Support pressing Enter to run the first command result.
- [x] Add compact styles for `.command-button`, `.command-overlay`, `.command-dialog`, and `.command-result`.
- [x] Re-run `cd webui && npm test -- --run src/App.test.tsx`.

## Task 2: Review Queue

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [x] Write a failing test that opens `复核`, sees `复核队列`, branch/candidate totals, selects `执行 unmerge`, types `人工复核通过`, and sees it in `决策预览`.
- [x] Run the focused test and confirm it fails because the review queue is not implemented.
- [x] Add local selected-candidate and operator-note state in `ReviewPanel`.
- [x] Render queue stats, candidate selection buttons, preview detail, and a separate `应用候选` action.
- [x] Style the review queue as dense panels and rows, avoiding large dashboard cards.
- [x] Re-run `cd webui && npm test -- --run src/App.test.tsx`.

## Task 3: Runtime Telemetry

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [x] Write a failing test that opens `指标` and verifies `运行遥测`, `Graph load`, `Event flow`, `Branch pressure`, and `Demo-ready`.
- [x] Run the focused test and confirm it fails because the telemetry layout is not implemented.
- [x] Replace the metric card grid with metric rows that expose label, value, status, and proportional bars.
- [x] Add API mode and patch health rows derived from current summary/demo data.
- [x] Add responsive CSS for `.telemetry-panel`, `.telemetry-row`, `.telemetry-bar`, and `.health-list`.
- [x] Re-run `cd webui && npm test -- --run src/App.test.tsx`.

## Task 4: Visual Regression

**Files:**
- Modify: `webui/scripts/visual-regression.mjs`

- [x] Add a desktop command-palette screenshot after pressing `Ctrl+K`.
- [x] Add a desktop review-queue screenshot after jumping to `复核`.
- [x] Add a desktop telemetry screenshot after jumping to `指标`.
- [x] Preserve existing console-error and overflow assertions.
- [x] Run `cd webui && npm run visual:check`.

## Final Verification

- [x] Run `cd webui && npm test -- --run`.
- [x] Run `cd webui && npm run build`.
- [x] Run `cd webui && npm run visual:check`.
- [x] Inspect generated screenshots for overlap, clipped modal content, mobile drawer regressions, and empty graph states.
