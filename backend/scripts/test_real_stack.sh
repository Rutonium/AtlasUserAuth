#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${1:-$ROOT_DIR/.env.local}"
SKIP_DB="${SKIP_DB:-0}"

if [[ "${2:-}" == "--skip-db" ]]; then
  SKIP_DB=1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  exit 1
fi

load_env_file() {
  local env_file="$1"
  eval "$(
    python3 - "$env_file" <<'PY'
import shlex
import sys
from pathlib import Path

path = Path(sys.argv[1])
for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    key = key.strip()
    if not key or not key.replace("_", "A").isalnum() or not (key[0].isalpha() or key[0] == "_"):
        continue
    print(f"export {key}={shlex.quote(value)}")
PY
  )"
}

load_env_file "$ENV_FILE"

required_vars=(
  ATLAS_AUTH_DB_URL
  EMPLOYEE_API_BASE_URL
  EMPLOYEE_API_TOKEN
  EMPLOYEE_API_AUTH_HEADER
)

for var_name in "${required_vars[@]}"; do
  if [[ -z "${!var_name:-}" ]]; then
    echo "Missing required env variable: $var_name"
    exit 1
  fi
done

if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  python3 -m venv "$ROOT_DIR/.venv"
fi
source "$ROOT_DIR/.venv/bin/activate"
pip install --upgrade pip >/dev/null
pip install -r "$ROOT_DIR/requirements.txt" >/dev/null

if [[ "$SKIP_DB" -eq 0 ]]; then
echo "Testing SQL connectivity..."
python3 - <<'PY'
import os
from sqlalchemy import create_engine, text

db_url = os.environ["ATLAS_AUTH_DB_URL"]
engine = create_engine(db_url, future=True, pool_pre_ping=True)

with engine.connect() as conn:
    conn.execute(text("SELECT 1"))
    try:
        row = conn.execute(text("SELECT TOP 1 EmployeeID FROM dbo.AtlasUsers")).first()
        print("DB OK: dbo.AtlasUsers reachable (sample EmployeeID: %s)" % (row[0] if row else "none"))
    except Exception as exc:
        print("DB connected, but dbo.AtlasUsers check failed: %s" % exc)
        raise
PY
else
  echo "Skipping SQL connectivity test (--skip-db)."
fi

echo "Testing employee directory API..."
AUTH_VALUE="$EMPLOYEE_API_TOKEN"
if [[ -n "${EMPLOYEE_API_AUTH_SCHEME:-}" ]]; then
  AUTH_VALUE="${EMPLOYEE_API_AUTH_SCHEME} ${EMPLOYEE_API_TOKEN}"
fi

EMPLOYEE_URL="${EMPLOYEE_API_BASE_URL%/}/Employees/all"
RESP_FILE="$(mktemp)"
HTTP_CODE="$(
  curl -sS \
    --max-time "${EMPLOYEE_API_TIMEOUT_SECONDS:-20}" \
    -H "${EMPLOYEE_API_AUTH_HEADER}: ${AUTH_VALUE}" \
    -o "$RESP_FILE" \
    -w '%{http_code}' \
    "$EMPLOYEE_URL"
)"

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "Employee API failed with HTTP $HTTP_CODE"
  echo "Response preview:"
  head -c 300 "$RESP_FILE" || true
  echo
  rm -f "$RESP_FILE"
  exit 1
fi

python3 - "$RESP_FILE" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8", errors="replace") as f:
    data = json.load(f)

if not isinstance(data, list):
    raise SystemExit("Employee API payload is not a list")

valid = 0
for row in data:
    if not isinstance(row, dict):
        continue
    if "number" in row and "name" in row:
        valid += 1

print(f"Employee API OK: received list with {len(data)} rows, {valid} rows with number+name")
PY

rm -f "$RESP_FILE"

PORT="${ATLAS_AUTH_PORT:-5020}"
if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then
  echo "Health endpoint OK: /healthz"
else
  echo "Note: app not running on 127.0.0.1:${PORT}, skipping HTTP health checks."
fi

echo "Real stack preflight passed."
