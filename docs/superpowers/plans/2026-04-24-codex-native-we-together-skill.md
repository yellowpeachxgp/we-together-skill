# Codex Native we-together Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, install, validate, and locally verify a Codex-native `we-together` skill that supports balanced Chinese auto-triggering for project-state, graph-runtime, and ingest workflows.

**Architecture:** Add a dedicated `codex_skill/` discovery package, implement reusable install/update/validate helpers under `src/we_together/packaging/`, and generate local runtime reference files at install time so the skill can resolve the repo root and MCP server from any current directory.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`/`shutil`, Codex local skills directory `~/.codex/skills`, existing `we-together-local-validate` MCP server, existing docs and runtime scripts.

---

## 1. Scope Lock

This plan covers:

- Codex-native skill package
- Chinese balanced trigger surface
- Local install/update/validate toolchain
- Install-time repo path injection
- Automated tests
- Local machine installation and verification

This plan does not cover:

- Further host-specific expansion beyond the current 7-skill family
- Codex internal routing changes
- A second MCP server

## 2. File Responsibility Map

### Skill package

- `codex_skill/SKILL.md`
  The main Codex-native skill entrypoint
- `codex_skill/agents/openai.yaml`
  UI metadata
- `codex_skill/prompts/dev.md`
  Project-status and continue-development behavior
- `codex_skill/prompts/runtime.md`
  Runtime graph / invariants / self-describe behavior
- `codex_skill/prompts/ingest.md`
  Import/bootstrap behavior
- `codex_skill/references/triggers.md`
  Trigger and non-trigger matrix
- `codex_skill/references/local-runtime.template.md`
  Template explanation for generated local runtime files

### Support module

- `src/we_together/packaging/codex_skill_support.py`
  Shared install/validate logic

### Scripts

- `scripts/install_codex_skill.py`
  Install entrypoint
- `scripts/update_codex_skill.py`
  Force-update entrypoint
- `scripts/validate_codex_skill.py`
  Source/install/config validation entrypoint

### Tests

- `tests/packaging/test_codex_skill_support.py`
  Unit tests for install, validation, and config detection

## 3. Delivery Phases

### Phase A: Freeze skill package shape

**Files:**
- Create: `codex_skill/SKILL.md`
- Create: `codex_skill/agents/openai.yaml`
- Create: `codex_skill/prompts/dev.md`
- Create: `codex_skill/prompts/runtime.md`
- Create: `codex_skill/prompts/ingest.md`
- Create: `codex_skill/references/triggers.md`
- Create: `codex_skill/references/local-runtime.template.md`

- [ ] **Step A1: Freeze skill name**

Set the Codex-native skill name to `we-together`.

- [ ] **Step A2: Freeze default install target**

Set the target install directory to `~/.codex/skills/we-together`.

- [ ] **Step A3: Freeze trigger strategy**

Use balanced Chinese triggering:

- trigger for explicit `we-together` project/runtime requests
- do not trigger for generic programming or generic social graph theory

- [ ] **Step A4: Write `codex_skill/SKILL.md` frontmatter**

The description must include:

- when to use
- Chinese trigger examples
- non-trigger boundary

- [ ] **Step A5: Write `codex_skill/SKILL.md` body**

It must instruct Codex to:

1. read `references/local-runtime.md` first
2. route to `prompts/dev.md`, `prompts/runtime.md`, or `prompts/ingest.md`
3. prefer MCP for graph meta ops
4. prefer `repo_root` for code/doc/test work

- [ ] **Step A6: Create `codex_skill/agents/openai.yaml`**

Add:

- display name
- short description
- default prompt

- [ ] **Step A7: Create `codex_skill/prompts/dev.md`**

Define behavior for:

- current status
- HANDOFF
- continue work
- Phase / ADR / invariant / baseline tasks

- [ ] **Step A8: Create `codex_skill/prompts/runtime.md`**

Define behavior for:

- graph summary
- list invariants
- check invariant
- self describe

- [ ] **Step A9: Create `codex_skill/prompts/ingest.md`**

Define behavior for:

- bootstrap
- import auto
- import file auto
- narration/text/email/directory import

- [ ] **Step A10: Create `codex_skill/references/triggers.md`**

List:

- strong triggers
- secondary runtime triggers
- explicit non-triggers

- [ ] **Step A11: Create `codex_skill/references/local-runtime.template.md`**

Explain that install-time files will be generated into the installed skill directory.

### Phase B: Build support module

**Files:**
- Create: `src/we_together/packaging/codex_skill_support.py`

- [ ] **Step B1: Define constants**

Add:

- default skill name
- default MCP server name
- required source files list

- [ ] **Step B2: Implement default target resolver**

Return `home/.codex/skills/we-together`.

- [ ] **Step B3: Implement source layout validation**

Check that all required skill package files exist before install.

- [ ] **Step B4: Implement installed layout validation**

Support `require_local_runtime=True` and require:

- `references/local-runtime.md`
- `references/local-runtime.json`

- [ ] **Step B5: Implement local runtime markdown renderer**

Render:

- repo root
- MCP server name
- preferred language
- HANDOFF path
- current-status path

- [ ] **Step B6: Implement local runtime json renderer**

Render the same information as JSON.

- [ ] **Step B7: Implement install flow**

The flow must:

1. validate source
2. respect `force`
3. copy the skill directory
4. write generated runtime files
5. re-validate installed layout

- [ ] **Step B8: Implement dry-run**

Allow reporting target paths without mutating disk.

- [ ] **Step B9: Implement Codex config MCP detection**

Check whether `~/.codex/config.toml` contains the target MCP registration table.

### Phase C: Build CLI scripts

**Files:**
- Create: `scripts/install_codex_skill.py`
- Create: `scripts/update_codex_skill.py`
- Create: `scripts/validate_codex_skill.py`

- [ ] **Step C1: Write install CLI argument parser**

Support:

- `--repo-root`
- `--source-dir`
- `--target-dir`
- `--skill-name`
- `--mcp-server-name`
- `--force`
- `--dry-run`

- [ ] **Step C2: Wire install CLI to support module**

Return JSON output and non-zero exit on failure.

- [ ] **Step C3: Write update CLI**

Make update a thin force-install wrapper around the install CLI.

- [ ] **Step C4: Write validate CLI argument parser**

Support:

- source validation
- installed validation
- explicit config path
- explicit server name

- [ ] **Step C5: Wire validate CLI to support module**

Validate:

- skill layout
- install-time runtime files
- MCP registration presence when `--installed` is used

### Phase D: TDD coverage

**Files:**
- Create: `tests/packaging/test_codex_skill_support.py`

- [ ] **Step D1: Write failing test for default target path**

Assert that a custom `home` yields `<home>/.codex/skills/we-together`.

- [ ] **Step D2: Write failing test for valid source skill tree**

Create a temp skill tree with all required files and assert validation passes.

- [ ] **Step D3: Write failing test for installed tree missing local runtime**

Require `local-runtime.*` and assert validation fails when those files are absent.

- [ ] **Step D4: Write failing test for install copy**

Assert install:

- copies `SKILL.md`
- creates `references/local-runtime.md`
- creates `references/local-runtime.json`

- [ ] **Step D5: Write failing test for runtime content**

Assert generated runtime files contain:

- repo root
- target MCP server name

- [ ] **Step D6: Write failing test for config detection**

Assert:

- matching server table returns true
- missing server table returns false

- [ ] **Step D7: Run focused test file**

Run:

```bash
.venv/bin/python -m pytest tests/packaging/test_codex_skill_support.py -q
```

- [ ] **Step D8: Run adjacent skill/runtime/packaging tests**

Run:

```bash
.venv/bin/python -m pytest tests/runtime/test_mcp_server.py tests/runtime/test_phase_33_skill_host.py tests/packaging/test_skill_packager.py tests/packaging/test_codex_skill_support.py -q
```

- [ ] **Step D9: Run full suite**

Run:

```bash
.venv/bin/python -m pytest -q
```

### Phase E: Local machine installation

**Files:**
- Modify: `~/.codex/skills/we-together/*` through installer output

- [ ] **Step E1: Install current repo into Codex skills**

Run:

```bash
.venv/bin/python scripts/install_codex_skill.py --force
```

- [ ] **Step E2: Validate source skill**

Run:

```bash
.venv/bin/python scripts/validate_codex_skill.py
```

- [ ] **Step E3: Validate installed skill**

Run:

```bash
.venv/bin/python scripts/validate_codex_skill.py --installed
```

- [ ] **Step E4: Read generated local runtime file**

Open the installed `references/local-runtime.md` and confirm:

- repo path points at this repository
- MCP server name matches `we-together-local-validate`

### Phase F: Interactive acceptance

**Files:**
- No code changes required if previous phases succeed

- [ ] **Step F1: Start Codex from a non-repo directory**

Use `~` or another unrelated directory.

- [ ] **Step F2: Trigger `we-together` with a status request**

Example:

```text
看一下 we-together 当前状态
```

- [ ] **Step F3: Trigger `we-together` with a runtime request**

Example:

```text
查一下这个 skill 的不变式
```

- [ ] **Step F4: Trigger `we-together` with a graph request**

Example:

```text
给我图谱摘要
```

- [ ] **Step F5: Trigger `we-together` with an ingest request**

Example:

```text
帮我导入一段人物材料
```

- [ ] **Step F6: Note any false-positive trigger cases**

If the skill steals unrelated prompts, tighten the trigger boundary.

- [ ] **Step F7: Note any false-negative trigger cases**

If obvious we-together prompts are missed, strengthen the trigger wording.

### Phase G: Documentation sync

**Files:**
- Modify: `docs/HANDOFF.md` if capability boundary changes
- Modify: `docs/superpowers/state/current-status.md` if capability boundary changes

- [ ] **Step G1: Re-evaluate whether Codex native skill support is now a formal capability**

- [ ] **Step G2: If yes, update handoff/current-status truthfully**

Only claim:

- skill package exists
- install/update/validate scripts exist
- local install was validated

Do not claim:

- every Chinese request always triggers perfectly

## 4. Execution Order

Strict order:

1. Phase A
2. Phase B
3. Phase C
4. Phase D
5. Phase E
6. Phase F
7. Phase G

## 5. Risks

- Trigger wording too aggressive can cause false positives
- Trigger wording too weak can cause false negatives
- Repo moves can stale-install the runtime path
- Codex skill activation remains heuristic, not hard routing

## 6. Rollback

### Remove installed skill

```bash
rm -rf ~/.codex/skills/we-together
```

### Remove repository changes

- `codex_skill/`
- `src/we_together/packaging/codex_skill_support.py`
- `scripts/install_codex_skill.py`
- `scripts/update_codex_skill.py`
- `scripts/validate_codex_skill.py`
- `tests/packaging/test_codex_skill_support.py`

## 7. Progress Tracker

- [x] Long design doc written
- [x] Long implementation plan written
- [ ] Phase A complete
- [ ] Phase B complete
- [ ] Phase C complete
- [ ] Phase D complete
- [ ] Phase E complete
- [ ] Phase F complete
- [ ] Phase G complete
