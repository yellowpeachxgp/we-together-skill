#!/usr/bin/env bash
# build_wheel.sh — 构建 sdist + wheel
set -euo pipefail

cd "$(dirname "$0")/.."

# 优先用 .venv 中的 python，否则回退到 python3
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
  else
    PY="python3"
  fi
fi

"$PY" -m pip install --upgrade build twine

rm -rf dist build *.egg-info

"$PY" -m build --sdist --wheel

echo ""
echo "产物："
ls -lh dist/

echo ""
echo "发布到 TestPyPI:"
echo "  $PY -m twine upload --repository testpypi dist/we_together-<version>-py3-none-any.whl dist/we_together-<version>.tar.gz"
echo ""
echo "发布到 PyPI（正式）:"
echo "  $PY -m twine upload dist/we_together-<version>-py3-none-any.whl dist/we_together-<version>.tar.gz"
