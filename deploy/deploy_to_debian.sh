#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_HOST="${ATLAS_DEPLOY_HOST:-}"
TARGET_USER="${ATLAS_DEPLOY_USER:-rune}"
TARGET_PATH="/home/rune/dev/atlas_user_auth"
SERVICE_NAME="atlas_user_auth"
ENV_FILE="/etc/atlas_user_auth/atlas_user_auth.env"
PORT="5020"

ALLOW_INTERACTIVE_AUTH=0
ALLOW_INTERACTIVE_SUDO=0
ALLOW_SHARED_FILE_CHANGES=0
INSTALL_ENV_FILE=0
INSTALL_SYSTEMD_UNIT=0
INSTALL_NGINX_SITE=0

for arg in "$@"; do
  case "$arg" in
    --allow-interactive-auth) ALLOW_INTERACTIVE_AUTH=1 ;;
    --allow-interactive-sudo) ALLOW_INTERACTIVE_SUDO=1 ;;
    --allow-shared-file-changes) ALLOW_SHARED_FILE_CHANGES=1 ;;
    --install-env-file) INSTALL_ENV_FILE=1 ;;
    --install-systemd-unit) INSTALL_SYSTEMD_UNIT=1 ;;
    --install-nginx-site) INSTALL_NGINX_SITE=1 ;;
    *) echo "Unknown flag: $arg"; exit 1 ;;
  esac
done

if [[ -z "$TARGET_HOST" ]]; then
  echo "Set ATLAS_DEPLOY_HOST before running deploy script."
  exit 1
fi

SSH_OPTS=""
if [[ "$ALLOW_INTERACTIVE_AUTH" -eq 1 ]]; then
  SSH_OPTS="-o PreferredAuthentications=publickey,password -o PubkeyAuthentication=yes"
fi

TMP_ARCHIVE="/tmp/atlas_user_auth_$(date +%Y%m%d_%H%M%S).tar.gz"

echo "Creating archive..."
tar -czf "$TMP_ARCHIVE" \
  --exclude=.git \
  --exclude=.venv \
  --exclude=venv \
  --exclude=node_modules \
  --exclude=dist \
  --exclude=__pycache__ \
  --exclude='*.pyc' \
  -C "$ROOT_DIR" .

echo "Uploading archive to ${TARGET_USER}@${TARGET_HOST}..."
scp $SSH_OPTS "$TMP_ARCHIVE" "${TARGET_USER}@${TARGET_HOST}:/tmp/atlas_user_auth.tar.gz"

REMOTE_CMD=$(cat <<'RCMD'
set -euo pipefail
mkdir -p /home/rune/dev/atlas_user_auth
rm -rf /home/rune/dev/atlas_user_auth/*
tar -xzf /tmp/atlas_user_auth.tar.gz -C /home/rune/dev/atlas_user_auth
python3 -m venv /home/rune/dev/atlas_user_auth/backend/.venv
/home/rune/dev/atlas_user_auth/backend/.venv/bin/pip install --upgrade pip
/home/rune/dev/atlas_user_auth/backend/.venv/bin/pip install -r /home/rune/dev/atlas_user_auth/backend/requirements.txt
RCMD
)

ssh $SSH_OPTS "${TARGET_USER}@${TARGET_HOST}" "$REMOTE_CMD"

if [[ "$ALLOW_SHARED_FILE_CHANGES" -eq 1 ]]; then
  if [[ "$INSTALL_ENV_FILE" -eq 1 ]]; then
    if [[ "$ALLOW_INTERACTIVE_SUDO" -ne 1 ]]; then
      echo "--install-env-file requires --allow-interactive-sudo"
      exit 1
    fi
    ssh $SSH_OPTS "${TARGET_USER}@${TARGET_HOST}" "sudo mkdir -p /etc/atlas_user_auth && sudo cp /home/rune/dev/atlas_user_auth/backend/.env.example ${ENV_FILE} && sudo chown root:root ${ENV_FILE} && sudo chmod 640 ${ENV_FILE}"
  fi

  if [[ "$INSTALL_SYSTEMD_UNIT" -eq 1 ]]; then
    if [[ "$ALLOW_INTERACTIVE_SUDO" -ne 1 ]]; then
      echo "--install-systemd-unit requires --allow-interactive-sudo"
      exit 1
    fi
    ssh $SSH_OPTS "${TARGET_USER}@${TARGET_HOST}" "sudo cp /home/rune/dev/atlas_user_auth/deploy/atlas_user_auth.service /etc/systemd/system/atlas_user_auth.service && sudo systemctl daemon-reload && sudo systemctl enable atlas_user_auth"
  fi

  if [[ "$INSTALL_NGINX_SITE" -eq 1 ]]; then
    if [[ "$ALLOW_INTERACTIVE_SUDO" -ne 1 ]]; then
      echo "--install-nginx-site requires --allow-interactive-sudo"
      exit 1
    fi
    ssh $SSH_OPTS "${TARGET_USER}@${TARGET_HOST}" "sudo cp /home/rune/dev/atlas_user_auth/deploy/nginx-atlas_user_auth.conf /etc/nginx/snippets/nginx-atlas_user_auth.conf && sudo nginx -t && sudo systemctl reload nginx"
  fi
fi

if [[ "$ALLOW_INTERACTIVE_SUDO" -eq 1 ]]; then
  ssh $SSH_OPTS "${TARGET_USER}@${TARGET_HOST}" "sudo systemctl restart ${SERVICE_NAME}"
  echo "Health checks..."
  ssh $SSH_OPTS "${TARGET_USER}@${TARGET_HOST}" "curl -fsS http://127.0.0.1:${PORT}/healthz && curl -fsS http://127.0.0.1:${PORT}/api/healthz"
else
  echo "Skipped service restart (no sudo)."
fi

echo "Deployment completed."
rm -f "$TMP_ARCHIVE"
