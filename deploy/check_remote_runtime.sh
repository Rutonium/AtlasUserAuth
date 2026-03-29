#!/usr/bin/env bash
set -euo pipefail

TARGET_HOST="${ATLAS_DEPLOY_HOST:-}"
TARGET_USER="${ATLAS_DEPLOY_USER:-rune}"
SERVICE_NAME="atlas_user_auth"
ENV_FILE="/etc/atlas_user_auth/atlas_user_auth.env"
PORT="5020"

if [[ -z "$TARGET_HOST" ]]; then
  echo "Set ATLAS_DEPLOY_HOST before running checks."
  exit 1
fi

ssh "${TARGET_USER}@${TARGET_HOST}" "
set -e
python3 --version
command -v pip3 >/dev/null
command -v systemctl >/dev/null
if [ -f ${ENV_FILE} ]; then
  echo 'env file: ok'
else
  echo 'env file: missing'
fi
sudo systemctl status ${SERVICE_NAME} --no-pager -n 40 || true
curl -fsS http://127.0.0.1:${PORT}/healthz || true
curl -fsS http://127.0.0.1:${PORT}/api/healthz || true
sudo journalctl -u ${SERVICE_NAME} -n 80 --no-pager || true
"
