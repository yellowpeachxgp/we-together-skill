# WebUI Operator Cockpit Phase 5 Design

## Purpose

Phase 5 moves the WebUI from a polished demo cockpit toward a production operator console. The first slice focuses on the operator-gated review path because it is the highest-risk workflow in the current UI: a human is deciding whether to keep a merged identity or apply an unmerge candidate.

## Approved Direction

The user approved the Phase 5 direction on 2026-04-29:

- make the cockpit more production-ready
- strengthen the real operator review flow
- improve maintainability after behavior is covered
- preserve the flat/liquid-glass visual system

## Architecture

The first implementation slice remains UI-only. It does not change backend write semantics, branch resolution APIs, migrations, or invariant behavior. The review queue adds richer operator context around the existing `Branch` and `BranchCandidate` data already present in `webui/src/App.tsx`.

The review flow should expose:

- risk level from confidence and candidate intent
- candidate diff/impact preview from `payload_json`
- explicit confirmation before applying a candidate
- operator note carried into the final preview
- responsive layout that stays dense but readable on mobile

## Components

- `ReviewPanel`: owns selected candidate and operator note state.
- `ReviewBranch`: renders branch copy, candidate list, risk summary, decision preview, and confirmation.
- future extraction target: `webui/src/components/ReviewPanel.tsx` once behavior is covered by tests.

## Data Flow

1. Branches load from demo data or `/api/branches?status=open`.
2. The highest-confidence candidate remains the default selection.
3. Selecting a candidate updates preview, risk, and impact rows.
4. The first click on `应用候选` opens a confirmation state.
5. The confirmation click calls the existing `onResolve(branch, selectedCandidate)` path.

## Visual System

The review queue should feel like an operational work surface, not a marketing card. Use compact rows, small labels, clear risk tone, and restrained accent colors. The design should keep the current liquid-glass material, but favor flat information hierarchy over decorative chrome.

## Testing

Vitest covers the branch review behavior:

- candidate selection updates preview
- risk summary is visible
- impact rows are rendered
- applying a candidate requires confirmation

Playwright visual regression covers:

- desktop review queue with risk summary and confirm state
- mobile drawer/layout constraints already covered by the broader cockpit check

## Self-Review

- No backend writes are changed.
- No schema or invariant behavior changes are required.
- The scope is a single implementation slice.
- Future modularization is explicitly deferred until the review behavior is covered.
