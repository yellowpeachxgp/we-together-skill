# WebUI Operator Cockpit Phase 5 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the operator review queue into a safer production workflow with risk summary, candidate impact preview, and explicit confirmation.

**Architecture:** Keep this slice UI-only. Extend the existing `ReviewPanel` and `ReviewBranch` behavior first, then extract the review components after tests protect the flow. The existing `onResolve(branch, candidate)` API remains the only branch resolution path.

**Tech Stack:** React 19, TypeScript, Vite, Vitest Testing Library, Playwright visual regression.

---

## File Structure

- Modify: `webui/src/App.test.tsx` for behavior-first tests.
- Modify: `webui/src/App.tsx` for the first implementation pass.
- Modify: `webui/src/styles.css` for review queue density, risk, and confirm styles.
- Modify: `webui/scripts/visual-regression.mjs` for review queue visual coverage.
- Create later: `webui/src/components/ReviewPanel.tsx` once behavior is covered and stable.

## Task 1: Review Risk And Impact Preview

- [x] **Step 1: Write the failing test**

Add a Vitest case that opens the review queue, selects `执行 unmerge`, and expects a `复核风险` region, high-risk copy, impact rows, and a confirmation button.

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/App.test.tsx`

Expected: FAIL because `复核风险` and confirmation are not rendered yet.

- [x] **Step 3: Write minimal implementation**

Add helper functions in `App.tsx`:

```ts
function getCandidateRisk(candidate?: BranchCandidate): "low" | "medium" | "high"
function getCandidateImpacts(candidate?: BranchCandidate): Array<{ label: string; value: string }>
```

Render risk and impact sections inside `ReviewBranch`.

- [x] **Step 4: Run focused test**

Run: `npm test -- --run src/App.test.tsx`

Expected: PASS.

## Task 2: Confirmation Before Apply

- [x] **Step 1: Write failing test**

Extend the review queue test to click `应用候选`, expect `确认应用`, then click confirmation and assert the demo result appears in the inspector JSON payload.

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/App.test.tsx`

Expected: FAIL because current button applies immediately.

- [x] **Step 3: Write minimal implementation**

Track pending confirmation in `ReviewBranch` with local state and reset it when the selected candidate changes.

- [x] **Step 4: Run focused test**

Run: `npm test -- --run src/App.test.tsx`

Expected: PASS.

## Task 3: Visual Regression Coverage

- [x] **Step 1: Extend Playwright review case**

Update `webui/scripts/visual-regression.mjs` to assert `复核风险`, `候选影响`, and `确认应用`, then capture the desktop review screenshot.

- [x] **Step 2: Run visual check**

Run: `npm run visual:check`

Expected: 2 Playwright checks pass and screenshots update under `output/playwright/`.

## Task 4: Final Verification

- [x] **Step 1: Full test suite**

Run: `npm test -- --run`

Expected: all WebUI tests pass.

- [x] **Step 2: Production build**

Run: `npm run build`

Expected: TypeScript and Vite build pass.

- [x] **Step 3: Visual regression**

Run: `npm run visual:check`

Expected: desktop and mobile visual checks pass.

## Task 5: Command Surface Productionization

- [x] **Step 1: Write the failing test**

Add a Vitest case that creates an active graph filter, opens the command palette, runs `Clear filters`, and expects the graph scope to return to `8 / 8 nodes`.

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/App.test.tsx`

Expected: FAIL because `Clear filters` is not a command palette action yet.

- [x] **Step 3: Write minimal implementation**

Add a command item:

```ts
{
  id: "action-clear-filters",
  group: "Actions",
  label: "Clear filters",
  meta: "scope",
  keywords: "Clear filters reset scope 清除 过滤 scope",
  run: clearFilters
}
```

Only show it when `hasActiveFilters` is true.

- [x] **Step 4: Extract CommandPalette**

Move the `CommandPalette` component and `CommandItem` type from `webui/src/App.tsx` into `webui/src/components/CommandPalette.tsx`. Keep props unchanged.

- [x] **Step 5: Run focused tests**

Run: `npm test -- --run src/App.test.tsx`

Expected: PASS.

- [x] **Step 6: Extend visual check**

Update the desktop command palette visual path to assert the `Clear filters` command after applying a filter.

## Task 6: Inspector Panel Productionization

- [x] **Step 1: Write the failing test**

Add a Vitest case that clicks the Inspector `聚焦当前` action and expects the filter status to show `Focus Alice` and `5 / 8 nodes`.

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/App.test.tsx`

Expected: FAIL because the Inspector does not expose a direct focus action yet.

- [x] **Step 3: Write minimal implementation**

Add an Inspector action button that calls the existing `focusSelectedNode()` path:

```tsx
<button type="button" onClick={onFocusCurrent}>
  <Maximize2 size={15} />
  聚焦当前
</button>
```

- [x] **Step 4: Extract InspectorPanel**

Move the Inspector JSX from `webui/src/App.tsx` into `webui/src/components/InspectorPanel.tsx`. Keep all existing callbacks as props and keep behavior unchanged.

- [x] **Step 5: Run focused tests**

Run: `npm test -- --run src/App.test.tsx`

Expected: PASS.

- [x] **Step 6: Extend visual check**

Update the desktop focus-lens path to use the Inspector `聚焦当前` action instead of only the canvas toolbar.

## Task 7: View Switch And Review Density Polish

- [x] **Step 1: Write the failing test**

Add a Vitest case that switches work surfaces and expects the viewport to reset to the top.

- [x] **Step 2: Run test to verify it fails**

Run: `npm test -- --run src/App.test.tsx`

Expected: FAIL because the current view switch preserves the prior scroll position.

- [x] **Step 3: Write minimal implementation**

Reset `window.scrollTo({ top: 0, left: 0 })` when the active view changes.

- [x] **Step 4: Extend visual check**

Assert the review confirmation state keeps `window.scrollY === 0` and compact the review decision panel so the high-risk confirmation path remains visible in the first desktop viewport.
