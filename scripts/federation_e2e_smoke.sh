#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="${TMPDIR:-/tmp}/wt_fed_smoke_$$"
PORT="${WE_TOGETHER_FED_SMOKE_PORT:-7798}"
TOKEN="${WE_TOGETHER_FED_SMOKE_TOKEN:-fed-smoke-token}"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "${SERVER_PID}" 2>/dev/null; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" >/dev/null 2>&1 || true
  fi
  rm -rf "${TMP_ROOT}"
}
trap cleanup EXIT

mkdir -p "${TMP_ROOT}"

cd "${ROOT_DIR}"
.venv/bin/python scripts/bootstrap.py --root "${TMP_ROOT}" >/dev/null
.venv/bin/python scripts/seed_demo.py --root "${TMP_ROOT}" >/dev/null

ALICE_ID="$(
  TMP_ROOT_FOR_PY="${TMP_ROOT}" .venv/bin/python - <<'PY'
import os
import sqlite3
from pathlib import Path
db = Path(os.environ["TMP_ROOT_FOR_PY"]) / "db" / "main.sqlite3"
conn = sqlite3.connect(db)
row = conn.execute("select person_id from persons order by primary_name limit 1").fetchone()
print(row[0])
conn.close()
PY
)"

WE_TOGETHER_FED_TOKENS="${TOKEN}" \
  .venv/bin/python scripts/federation_http_server.py \
  --root "${TMP_ROOT}" \
  --host 127.0.0.1 \
  --port "${PORT}" \
  --enable-write >/dev/null 2>&1 &
SERVER_PID=$!
sleep 1

echo "[1/7] capabilities"
curl -fsS "http://127.0.0.1:${PORT}/federation/v1/capabilities" | \
  python3 -c 'import json, sys; payload = json.load(sys.stdin); assert payload["write_enabled"] is True; assert payload["read_only"] is False' >/dev/null

echo "[2/7] unauthorized persons -> 401"
STATUS="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/federation/v1/persons?limit=2")"
[[ "${STATUS}" == "401" ]]

echo "[3/7] authorized persons -> 200"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "http://127.0.0.1:${PORT}/federation/v1/persons?limit=2" | python3 -m json.tool >/dev/null

echo "[4/7] invalid payload -> 422"
STATUS="$(curl -s -o /dev/null -w '%{http_code}' \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"summary":"","owner_person_ids":[]}' \
  "http://127.0.0.1:${PORT}/federation/v1/memories")"
[[ "${STATUS}" == "422" ]]

echo "[5/7] create memory -> 201"
curl -fsS \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST \
  -d "{\"summary\":\"federation smoke memory\",\"owner_person_ids\":[\"${ALICE_ID}\"],\"source_skill_name\":\"smoke\"}" \
  "http://127.0.0.1:${PORT}/federation/v1/memories" | python3 -m json.tool >/dev/null

echo "[6/7] get person -> 200"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "http://127.0.0.1:${PORT}/federation/v1/persons/${ALICE_ID}" | python3 -m json.tool >/dev/null

echo "[7/7] list memories -> 200"
curl -fsS -H "Authorization: Bearer ${TOKEN}" \
  "http://127.0.0.1:${PORT}/federation/v1/memories?owner_id=${ALICE_ID}&limit=5" | python3 -m json.tool >/dev/null

echo "federation_e2e_smoke: ok"
