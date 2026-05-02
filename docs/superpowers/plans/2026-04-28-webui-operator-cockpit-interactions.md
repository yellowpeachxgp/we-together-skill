# WebUI Operator Cockpit Interactions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the selected Operator Cockpit WebUI from a polished static dashboard into a usable graph operations surface.

**Architecture:** Keep the existing React/Vite app structure and add scoped interaction state inside `App.tsx`. Preserve the three-column cockpit, using small helper components for graph controls, activity records, inspector context, and operational states instead of a broad file split.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, Playwright CLI wrapper.

---

## Visual And Interaction Thesis

Visual thesis: dense calm console, glass/flat material, graph canvas as the primary working surface.

Interaction thesis:
- Graph controls should feel immediate: zoom in/out, fit to view, hover to reveal relationships, click edges for detail.
- Audit records should be operational objects: clicking a record changes the inspector and highlights related nodes.
- Mobile should use an inspector drawer so the canvas remains the first working surface.

## Todo

- [ ] Add tests for graph zoom, pan affordance, fit-to-view, edge detail inspection, and hover relationship highlighting.
- [ ] Add tests for activity record click-through, related-node highlighting, pinned selection, comparison, and recent history.
- [ ] Add tests for mobile drawer affordance and operational states: empty, loading, error, permission/token, long text.
- [ ] Implement graph viewport state with zoom controls, fit reset, draggable panning, edge buttons, and edge/node highlight classes.
- [ ] Implement clickable activity records with inferred related-node highlighting and inspector context switching.
- [ ] Upgrade inspector with pin, compare, recent history, edge/activity render modes, and long-text handling.
- [ ] Convert mobile inspector into a bottom drawer with explicit open/close controls.
- [ ] Add empty, loading skeleton, API error, demo/no-token, and no-result states without adding marketing copy.
- [ ] Add a visual regression script under `webui/scripts/visual-regression.mjs` and expose it through `npm run visual:check`.
- [ ] Verify with Vitest, production build, and Playwright screenshots at desktop and mobile sizes.

## Files

- Modify: `webui/src/App.tsx`
- Modify: `webui/src/styles.css`
- Modify: `webui/src/App.test.tsx`
- Modify: `webui/package.json`
- Create: `webui/scripts/visual-regression.mjs`

## Execution Notes

- Use TDD for observable behavior before production code.
- Keep cards restrained; favor toolbars, lists, drawers, and separators.
- Do not change backend APIs. Demo data must continue to work without a token.
- Do not revert unrelated dirty worktree changes.
