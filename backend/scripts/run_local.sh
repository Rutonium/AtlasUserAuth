#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

if [[ ! -f .env.local ]]; then
  cat > .env.local <<'EOL'
ATLAS_AUTH_DB_URL=sqlite+pysqlite:///./local_dev.db
ATLAS_AUTH_PORT=5020

SESSION_SIGNING_SECRET=dev-only-change-me
SESSION_IDLE_TIMEOUT_SECONDS=1800
SESSION_ABSOLUTE_TIMEOUT_SECONDS=43200
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_DOMAIN=
SESSION_COOKIE_PATH=/

LOCAL_ADMIN_PASSWORD=devpass
LOCAL_ADMIN_EMPLOYEE_ID=0
LOCAL_ADMIN_NAME="Local Admin"

CORS_ALLOW_ORIGINS=http://127.0.0.1:5020,http://localhost:5020
CORS_ALLOW_CREDENTIALS=true

EMPLOYEE_API_BASE_URL=http://localhost:9999
EMPLOYEE_API_TOKEN=dev-token
EMPLOYEE_API_AUTH_HEADER=Authorization
EMPLOYEE_API_AUTH_SCHEME=
EMPLOYEE_API_TIMEOUT_SECONDS=2
EMPLOYEE_CACHE_TTL_SECONDS=300

AUTH_ATTEMPT_WINDOW_SECONDS=300
AUTH_MAX_ATTEMPTS_PER_IP=50
AUTH_MAX_ATTEMPTS_PER_ACCOUNT=8
AUTH_LOCKOUT_SECONDS=900
EOL
  echo "Created backend/.env.local (dev defaults)."
fi

# Backward-compatible fix for older generated env files.
if grep -q '^LOCAL_ADMIN_NAME=Local Admin$' .env.local; then
  sed -i 's/^LOCAL_ADMIN_NAME=Local Admin$/LOCAL_ADMIN_NAME="Local Admin"/' .env.local
fi

set -a
source .env.local
set +a

export PYTHONPATH="$ROOT_DIR"
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${ATLAS_AUTH_PORT:-5020}" --reload
