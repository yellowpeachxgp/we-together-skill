#!/usr/bin/env bash
set -euo pipefail

WE_TOGETHER_REPO_URL="${WE_TOGETHER_REPO_URL:-https://github.com/yellowpeach/we-together-skill.git}"
WE_TOGETHER_HOME="${WE_TOGETHER_HOME:-$HOME/.we-together}"
WE_TOGETHER_CODEX_HOME="${WE_TOGETHER_CODEX_HOME:-$HOME/.codex}"
WE_TOGETHER_INSTALL_MODE="${WE_TOGETHER_INSTALL_MODE:-editable}"
WE_TOGETHER_MCP_SERVER_NAME="${WE_TOGETHER_MCP_SERVER_NAME:-we-together-local-validate}"

REPO_DIR="${WE_TOGETHER_HOME}/repo"
VENV_DIR="${WE_TOGETHER_HOME}/venv"
DATA_DIR="${WE_TOGETHER_HOME}/data"
SKILLS_DIR="${WE_TOGETHER_CODEX_HOME}/skills"
CONFIG_PATH="${WE_TOGETHER_CODEX_HOME}/config.toml"

log() {
  printf '[we-together install] %s\n' "$*"
}

fail() {
  printf '[we-together install] ERROR: %s\n' "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing required command: $1"
}

python_version_check() {
  python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required")
PY
}

git_clone_or_update() {
  mkdir -p "$WE_TOGETHER_HOME"
  if [ -d "$REPO_DIR/.git" ]; then
    log "updating repo at $REPO_DIR"
    git -C "$REPO_DIR" fetch --all --tags --prune
    git -C "$REPO_DIR" pull --ff-only
  elif [ -d "$REPO_DIR" ]; then
    fail "$REPO_DIR exists but is not a git repository"
  else
    log "cloning repo into $REPO_DIR"
    git clone "$WE_TOGETHER_REPO_URL" "$REPO_DIR"
  fi
}

install_python_package() {
  if [ ! -x "$VENV_DIR/bin/python" ]; then
    log "creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  fi
  log "upgrading pip"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip
  if [ "$WE_TOGETHER_INSTALL_MODE" = "editable" ]; then
    log "installing package in editable mode"
    "$VENV_DIR/bin/python" -m pip install -e "$REPO_DIR"
  elif [ "$WE_TOGETHER_INSTALL_MODE" = "regular" ]; then
    log "installing package in regular mode"
    "$VENV_DIR/bin/python" -m pip install "$REPO_DIR"
  else
    fail "unsupported WE_TOGETHER_INSTALL_MODE: $WE_TOGETHER_INSTALL_MODE"
  fi
}

bootstrap_runtime() {
  mkdir -p "$DATA_DIR" "$WE_TOGETHER_CODEX_HOME"
  log "bootstrapping data root at $DATA_DIR"
  "$VENV_DIR/bin/we-together" bootstrap --root "$DATA_DIR"
}

install_codex_skill_family() {
  log "installing Codex skill family into $SKILLS_DIR"
  "$VENV_DIR/bin/python" "$REPO_DIR/scripts/install_codex_skill.py" \
    --repo-root "$REPO_DIR" \
    --family \
    --force \
    --target-dir "$SKILLS_DIR" \
    --mcp-server-name "$WE_TOGETHER_MCP_SERVER_NAME" \
    --configure-mcp \
    --config-path "$CONFIG_PATH" \
    --mcp-root "$DATA_DIR" \
    --python-bin "$VENV_DIR/bin/python" \
    --force-mcp
}

validate_install() {
  log "validating CLI"
  "$VENV_DIR/bin/we-together" version
  log "validating Codex skill family"
  "$VENV_DIR/bin/python" "$REPO_DIR/scripts/validate_codex_skill.py" \
    --installed \
    --family \
    --skill-dir "$SKILLS_DIR" \
    --config-path "$CONFIG_PATH" \
    --mcp-server-name "$WE_TOGETHER_MCP_SERVER_NAME"
}

main() {
  need_cmd git
  need_cmd python3
  python_version_check
  git_clone_or_update
  install_python_package
  bootstrap_runtime
  install_codex_skill_family
  validate_install

  log "installed"
  printf '\n'
  printf 'Repo:   %s\n' "$REPO_DIR"
  printf 'Data:   %s\n' "$DATA_DIR"
  printf 'Skills: %s\n' "$SKILLS_DIR"
  printf 'MCP:    %s in %s\n' "$WE_TOGETHER_MCP_SERVER_NAME" "$CONFIG_PATH"
  printf '\n'
  printf 'Restart Codex, then ask: 看一下 we-together 当前状态\n'
}

main "$@"
