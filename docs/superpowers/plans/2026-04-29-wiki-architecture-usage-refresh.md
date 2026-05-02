# Wiki Architecture And Usage Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the project-facing Wiki and entry docs so architecture, usage, capabilities, and interaction flows match the current v0.19.0 code baseline.

**Architecture:** Add `docs/wiki/` as the stable reader-facing knowledge base, then update older docs entrypoints to point at it and remove stale v0.9/v0.16/Phase-1 claims. Ground all claims in executable evidence: CLI version/help, `self_audit.py`, invariant summary, WebUI bridge status, and current-status/HANDOFF.

**Tech Stack:** Markdown documentation, existing Python CLI scripts, local MCP self-description, shell verification.

---

## Baseline Evidence

- `scripts/self_audit.py`: v0.19.0, 73 ADR, 28 covered invariants, 21 migrations, 84 services, 75 scripts.
- `scripts/invariants_check.py summary`: 28/28 invariants covered.
- `.venv/bin/we-together --help`: public CLI includes `webui` / `webui-host`.
- `docs/HANDOFF.md` and `docs/superpowers/state/current-status.md`: latest persistent handoff and development state.
- `scripts/webui_host.py` and WebUI curl smoke: browser default path is local skill bridge, no WebUI token required.

## Task 1: Create Wiki Landing Pages

**Files:**
- Create: `docs/wiki/README.md`
- Create: `docs/wiki/architecture.md`
- Create: `docs/wiki/capabilities.md`
- Create: `docs/wiki/usage.md`
- Create: `docs/wiki/interaction-flows.md`

- [x] **Step 1: Create the Wiki home**

Include a concise reader map, current baseline, and links to architecture, usage, capabilities, and interaction flows.

- [x] **Step 2: Create architecture page**

Document layers, storage, event-first graph evolution, host/runtime boundaries, WebUI local bridge, and tenant routing.

- [x] **Step 3: Create capability page**

Separate confirmed capabilities, advanced/provider-dependent capabilities, and known limits.

- [x] **Step 4: Create usage page**

Document local install, bootstrap, seed/import, CLI run-turn, WebUI, Codex skill family, and verification commands.

- [x] **Step 5: Create interaction flow page**

Document CLI, WebUI, Codex/MCP, import, operator review, maintenance/tick, and multi-tenant flows.

## Task 2: Refresh Existing Entry Docs

**Files:**
- Modify: `docs/index.md`
- Modify: `docs/architecture/overview.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/getting-started.md`
- Modify: `docs/FAQ.md`
- Modify: `docs/superpowers/README.md`
- Modify: `README.md`

- [x] **Step 1: Update `docs/index.md`**

Make it v0.19.0-aware and link `docs/wiki/`.

- [x] **Step 2: Update quickstart/getting-started**

Replace stale migration/test/version claims and add WebUI local bridge usage.

- [x] **Step 3: Update architecture overview**

Promote v0.19 architecture and defer details to Wiki pages.

- [x] **Step 4: Update FAQ**

Fix stale ingest commands and clarify local-only storage, provider keys, and WebUI token behavior.

- [x] **Step 5: Update superpowers README and root README**

Add Wiki link and current fact patch so old readers find the maintained entrypoint.

## Task 3: Verification

**Files:**
- Read all modified docs.

- [x] **Step 1: Run code-fact checks**

Run:

```bash
.venv/bin/we-together version
.venv/bin/we-together --help
.venv/bin/python scripts/self_audit.py
.venv/bin/python scripts/invariants_check.py summary
```

Expected: v0.19.0, CLI exposes WebUI commands, self-audit and invariants match Wiki facts.

- [x] **Step 2: Scan stale facts**

Run:

```bash
rg -n "v0\\.9|v0\\.16|15 条 migration|ADR 33|Phase 1 基础|288 passed|594 passed|当前版本.*v0\\.16|dialogue-turn[\\s\\S]*--input|we-together ingest|import-email" docs/index.md docs/quickstart.md docs/getting-started.md docs/architecture/overview.md docs/FAQ.md docs/wiki docs/superpowers/README.md docs/superpowers/architecture/README.md
```

Expected: no stale facts in refreshed entry docs. Root `README.md` keeps historical phase notes, so this scan only checks the refreshed first-class entry docs.

- [x] **Step 3: Check key links exist**

Check all new Wiki target files and linked canonical docs exist.

## Self-Review Checklist

- [x] **Spec coverage:** Wiki covers architecture, usage, capabilities, and interaction flows.
- [x] **Fact grounding:** Numeric claims cite current code/MCP/script evidence.
- [x] **Scope boundary:** Docs distinguish default mock/local mode from real-provider and remote-token advanced modes.
- [x] **No stale-first-screen:** Main entry docs no longer lead with v0.9/v0.16/Phase-1 status.
