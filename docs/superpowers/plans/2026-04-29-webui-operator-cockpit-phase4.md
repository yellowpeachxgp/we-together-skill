# WebUI Operator Cockpit Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continue the Operator Cockpit by adding a graph focus workflow: operators can isolate a selected node's neighborhood, jump through related nodes from Inspector, and invoke focus from the command palette.

**Architecture:** Keep the current React single-file cockpit for this pass. Add a small focus lens state in `App.tsx`, derive neighbor nodes from graph edges, thread the lens through existing filters, and keep all visual changes in `styles.css`. Preserve backend invariants by keeping this pass UI-only.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, Playwright.

---

## Visual And Interaction Thesis

Visual thesis: the graph view should feel like an operator lens, not a static canvas; selected entities need an immediate, low-noise path to their local context.

Interaction thesis:
- A selected node should expose a one-click neighborhood focus without forcing the operator to type filters.
- Inspector should show direct graph neighbors as actionable links.
- Command palette should include the current selection workflow, so keyboard operators can focus without leaving flow.

## Todo

- [x] Add failing tests for graph neighborhood focus and reset.
- [x] Add failing tests for Inspector related-node navigation.
- [x] Add failing tests for command-palette focus action.
- [x] Implement selected-node neighbor derivation and focus lens filtering.
- [x] Render focus controls in graph toolbar and status chips.
- [x] Render Inspector direct-neighbor list with click-to-select.
- [x] Add command item for focusing the current selection.
- [x] Style the focus lens and related-node list responsively.
- [x] Extend visual regression with a desktop focus-lens screenshot.
- [x] Verify with Vitest, production build, Playwright visual checks, and screenshot inspection.

## Task 1: Focus Lens Tests

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [x] Write a failing test that selects `Alice`, clicks `聚焦邻域`, sees a `Focus Alice` status chip, and sees only Alice plus direct neighbors.
- [x] Write a failing test that clears filters after focusing and restores `8 / 8 nodes`.
- [x] Run `cd webui && npm test -- --run src/App.test.tsx` and confirm failures are caused by missing focus lens UI.

## Task 2: Inspector Related Nodes

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`

- [x] Write a failing test that selects `Alice`, sees `关联节点`, clicks `Bob`, and verifies Inspector shows `person_bob`.
- [x] Add derived related-node data from graph edges and selected node.
- [x] Render a compact related-node list inside Inspector for node selections.
- [x] Re-run `cd webui && npm test -- --run src/App.test.tsx`.

## Task 3: Command Focus Action

**Files:**
- Test: `webui/src/App.test.tsx`
- Modify: `webui/src/App.tsx`

- [x] Write a failing test that opens the command palette, runs `Focus Alice`, and sees the focus status chip.
- [x] Add a selection-aware command item that applies the current focus lens.
- [x] Re-run `cd webui && npm test -- --run src/App.test.tsx`.

## Task 4: Visual Regression

**Files:**
- Modify: `webui/scripts/visual-regression.mjs`

- [x] Add a desktop screenshot for the focused-neighborhood graph.
- [x] Preserve existing console-error and overflow assertions.
- [x] Run `cd webui && npm run visual:check`.

## Final Verification

- [x] Run `cd webui && npm test -- --run`.
- [x] Run `cd webui && npm run build`.
- [x] Run `cd webui && npm run visual:check`.
- [x] Inspect generated screenshots for overlap, clipped Inspector related nodes, command modal regressions, and mobile overflow.
