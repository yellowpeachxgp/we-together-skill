#!/usr/bin/env bash
# 本地工程化检查：ruff (必须过) + mypy (报告式)
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${REPO_ROOT}/.venv/bin/python"

echo "===> ruff check"
"${PY}" -m ruff check src scripts

echo "===> ruff format --check"
"${PY}" -m ruff format --check src scripts || echo "(format suggestions exist; run 'ruff format src scripts' to auto-apply)"

echo "===> mypy (advisory — 当前允许存在剩余 warning)"
"${PY}" -m mypy src/we_together || true

echo "===> pytest"
"${PY}" -m pytest -q

echo "===> all checks passed"
