# Zero Config Install Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a verified one-command installer so a new machine can install we-together, its Codex skill family, and its MCP registration without manual configuration.

**Architecture:** Keep orchestration in `scripts/install.sh`; keep idempotent Codex TOML editing in Python so it is unit-testable. Existing `install_codex_skill.py` remains the skill-family installer and gains MCP registration flags.

**Tech Stack:** POSIX shell, Python stdlib, TOML-compatible text block management, pytest.

---

### Task 1: MCP Config Writer

**Files:**
- Modify: `src/we_together/packaging/codex_skill_support.py`
- Test: `tests/packaging/test_codex_skill_support.py`

- [ ] Add tests for managed MCP config insertion.
- [ ] Add tests for idempotent replacement.
- [ ] Add tests that non-managed same-name config is not overwritten unless forced.
- [ ] Implement `build_codex_mcp_server_block(...)` and `upsert_codex_mcp_server_config(...)`.

### Task 2: Install CLI MCP Flags

**Files:**
- Modify: `scripts/install_codex_skill.py`
- Test: `tests/packaging/test_codex_skill_support.py`

- [ ] Add a failing CLI test for `--configure-mcp`.
- [ ] Add `--config-path`, `--mcp-root`, `--python-bin`, and `--force-mcp`.
- [ ] Include MCP config report fields in JSON output.

### Task 3: One Command Shell Installer

**Files:**
- Create: `scripts/install.sh`
- Test: `tests/packaging/test_zero_config_install_script.py`

- [ ] Add static tests for required shell behavior and defaults.
- [ ] Implement strict shell options and env overrides.
- [ ] Clone or update repo into `${WE_TOGETHER_HOME}/repo`.
- [ ] Create venv at `${WE_TOGETHER_HOME}/venv`.
- [ ] Install package, bootstrap data, install skill family, configure MCP, validate.

### Task 4: Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/getting-started.md`
- Modify: `docs/hosts/codex.md`
- Modify: `docs/wiki/usage.md`

- [ ] Make one-command install the primary path.
- [ ] Keep manual install as development path.
- [ ] Document zero-config boundary and env overrides.

### Task 5: Verification

**Files:**
- No production files.

- [ ] Run focused pytest for packaging installer tests.
- [ ] Run a temp HOME install smoke using `WE_TOGETHER_REPO_URL=file://$PWD`.
- [ ] Run installed skill-family validation against the temp Codex home.
- [ ] Run full pytest.
- [ ] Run release strict E2E if full pytest is clean.
