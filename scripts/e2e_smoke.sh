#!/usr/bin/env bash
# 端到端烟测：从空白 root 走一遍完整链路。
# 所有 LLM 调用通过 mock provider，无需网络/API Key。

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${REPO_ROOT}/.venv/bin/python"
TMP_ROOT="${E2E_TMP_ROOT:-$(mktemp -d -t wt-e2e-XXXXXX)}"

echo "===> 使用临时 root: ${TMP_ROOT}"

cd "${REPO_ROOT}"

echo "[1/10] bootstrap"
"${PY}" scripts/bootstrap.py --root "${TMP_ROOT}" >/dev/null

echo "[2/10] seed_demo"
SEED_JSON=$("${PY}" scripts/seed_demo.py --root "${TMP_ROOT}")
WORK_SCENE=$("${PY}" -c "import json,sys; print(json.loads(sys.stdin.read())['scenes']['work'])" <<< "${SEED_JSON}")
DATE_SCENE=$("${PY}" -c "import json,sys; print(json.loads(sys.stdin.read())['scenes']['date'])" <<< "${SEED_JSON}")

echo "[3/10] build_retrieval_package (work scene)"
"${PY}" scripts/build_retrieval_package.py --root "${TMP_ROOT}" --scene-id "${WORK_SCENE}" >/dev/null

echo "[4/10] build_retrieval_package (date scene)"
"${PY}" scripts/build_retrieval_package.py --root "${TMP_ROOT}" --scene-id "${DATE_SCENE}" >/dev/null

echo "[5/10] dialogue_turn"
"${PY}" scripts/dialogue_turn.py --root "${TMP_ROOT}" --scene-id "${WORK_SCENE}" \
  --user-input "今天各自的进度如何？" --response-text "[mock]" >/dev/null

echo "[6/10] snapshot list"
"${PY}" scripts/snapshot.py --root "${TMP_ROOT}" list >/dev/null

echo "[7/10] relation drift"
"${PY}" scripts/drift.py --root "${TMP_ROOT}" --window-days 30 >/dev/null

echo "[8/10] state decay"
"${PY}" scripts/decay.py --root "${TMP_ROOT}" >/dev/null

echo "[9/10] merge_duplicates"
"${PY}" scripts/merge_duplicates.py --root "${TMP_ROOT}" >/dev/null

echo "[10/13] graph_summary"
"${PY}" scripts/graph_summary.py --root "${TMP_ROOT}" >/dev/null

echo "[11/13] import_llm (mock provider)"
"${PY}" scripts/import_llm.py --root "${TMP_ROOT}" --text "Alice 和 Bob 是同事。" --source-name e2e --provider mock >/dev/null

echo "[12/13] auto_resolve_branches"
"${PY}" scripts/auto_resolve_branches.py --root "${TMP_ROOT}" --threshold 0.7 --margin 0.1 >/dev/null

echo "[13/13] self_activate"
"${PY}" scripts/self_activate.py --root "${TMP_ROOT}" --scene-id "${WORK_SCENE}" --daily-budget 2 --per-run 1 --provider mock >/dev/null

echo "===> OK"
