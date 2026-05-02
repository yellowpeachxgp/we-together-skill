# WebUI Overall Audit + Optimization Plan — 2026-04-29

## Code-Truth Baseline

- confirmed: `webui/` is a React 19 + TypeScript + Vite operator cockpit with Vitest and Playwright visual checks.
- confirmed: the main UI behavior is concentrated in `webui/src/App.tsx` at 1840 lines. It includes demo data, API client, graph layout helpers, app state, command palette, graph canvas, activity dock, review queue, metrics, world, chat, and inspector.
- confirmed: current tests live in `webui/src/App.test.tsx` and cover shell rendering, theme switch, graph selection, edge selection, activity detail, inspector pin/compare/history, filtering, focus lens, lane tabs, shortcuts, clipboard copy, command palette, review queue, and telemetry.
- confirmed: visual regression lives in `webui/scripts/visual-regression.mjs`, generating desktop/mobile screenshots plus desktop focus, command palette, activity, review, and telemetry states.
- confirmed: this WebUI phase is UI-only and must not weaken backend invariants: event-first writes, reversible operator-gated unmerge, versioned schemas, and snapshot-aware operations remain backend responsibilities.

## Visual Thesis

Keep the cockpit dense and calm: flat operational hierarchy, liquid-glass material only where it clarifies separation, compact command-driven interaction, and mobile controls that read as deliberate rather than squeezed.

## Audit Findings

- The command palette is useful but still half-keyboarded: `Enter` always runs the first result, while arrow navigation and active-result feedback are absent.
- Mobile navigation currently allows short Chinese labels to wrap vertically, making the app feel less finished on narrow screens.
- The inspector has strong detail density, but it lacks a compact context strip that tells the operator how many direct relations, recent items, and current mode they are looking at before scanning raw fields.
- Visual regression covers the main surfaces, but it does not yet assert the new keyboard-active command state or mobile navigation polish.
- `App.tsx` is ready for future modularization, but behavior polish should land first so the extraction has stronger regression coverage.

## TODO

1. Add failing tests for command palette arrow navigation and active-result execution.
2. Implement active command index, `ArrowUp` / `ArrowDown`, `Enter`, `Escape`, and visible selected-result styling.
3. Add an inspector context strip for relation count, recent count, and selection mode.
4. Tighten mobile navigation and compact controls so labels stay readable without vertical wrapping.
5. Extend Playwright visual checks for active command selection and mobile drawer context.
6. Run `npm test -- --run`, `npm run build`, and `npm run visual:check`; inspect updated screenshots before reporting completion.

## Deferred

- Split `App.tsx` into typed modules after this behavior pass, likely `data.ts`, `graph.ts`, `components/CommandPalette.tsx`, `components/Inspector.tsx`, and `components/GraphWorkspace.tsx`.
- Add API integration contract tests once the backend WebUI endpoints are considered stable.
