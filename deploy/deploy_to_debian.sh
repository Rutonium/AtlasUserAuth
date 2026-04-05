#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_HOST="${ATLAS_DEPLOY_HOST:-}"
TARGET_USER="${ATLAS_DEPLOY_USER:-rune}"
TARGET_PATH="${ATLAS_DEPLOY_PATH:-/home/rune/dev/atlas_user_auth}"
APP_OWNER="${ATLAS_APP_OWNER:-rune}"
APP_GROUP="${ATLAS_APP_GROUP:-$APP_OWNER}"
SSH_MODE="${ATLAS_SSH_MODE:-ssh}"
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

SSH_OPTS=()
if [[ "$SSH_MODE" == "ssh" && "$ALLOW_INTERACTIVE_AUTH" -eq 1 ]]; then
  SSH_OPTS=(-o PreferredAuthentications=publickey,password -o PubkeyAuthentication=yes)
fi

TMP_ARCHIVE="/tmp/atlas_user_auth_$(date +%Y%m%d_%H%M%S).tar.gz"
REMOTE_ARCHIVE="/tmp/atlas_user_auth.tar.gz"

remote_exec() {
  local remote_cmd="$1"
  if [[ "$SSH_MODE" == "tailscale" ]]; then
    tailscale ssh "${TARGET_USER}@${TARGET_HOST}" "$remote_cmd"
  else
    ssh "${SSH_OPTS[@]}" "${TARGET_USER}@${TARGET_HOST}" "$remote_cmd"
  fi
}

remote_copy() {
  local source_file="$1"
  local destination_file="$2"
  if [[ "$SSH_MODE" == "tailscale" ]]; then
    tailscale ssh "${TARGET_USER}@${TARGET_HOST}" "cat > ${destination_file}" < "$source_file"
  else
    scp "${SSH_OPTS[@]}" "$source_file" "${TARGET_USER}@${TARGET_HOST}:${destination_file}"
  fi
}

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
remote_copy "$TMP_ARCHIVE" "$REMOTE_ARCHIVE"

REMOTE_CMD=$(cat <<'RCMD'
set -euo pipefail
install -d -m 775 -o __APP_OWNER__ -g __APP_GROUP__ __TARGET_PATH__
find __TARGET_PATH__ -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar -xzf __REMOTE_ARCHIVE__ -C __TARGET_PATH__
chown -R __APP_OWNER__:__APP_GROUP__ __TARGET_PATH__
runuser -u __APP_OWNER__ -- python3 -m venv __TARGET_PATH__/backend/.venv
runuser -u __APP_OWNER__ -- __TARGET_PATH__/backend/.venv/bin/pip install --upgrade pip
runuser -u __APP_OWNER__ -- __TARGET_PATH__/backend/.venv/bin/pip install -r __TARGET_PATH__/backend/requirements.txt
RCMD
)

REMOTE_CMD="${REMOTE_CMD//__TARGET_PATH__/$TARGET_PATH}"
REMOTE_CMD="${REMOTE_CMD//__APP_OWNER__/$APP_OWNER}"
REMOTE_CMD="${REMOTE_CMD//__APP_GROUP__/$APP_GROUP}"
REMOTE_CMD="${REMOTE_CMD//__REMOTE_ARCHIVE__/$REMOTE_ARCHIVE}"

remote_exec "$REMOTE_CMD"

if [[ "$ALLOW_SHARED_FILE_CHANGES" -eq 1 ]]; then
  if [[ "$INSTALL_ENV_FILE" -eq 1 ]]; then
    if [[ "$ALLOW_INTERACTIVE_SUDO" -ne 1 ]]; then
      echo "--install-env-file requires --allow-interactive-sudo"
      exit 1
    fi
    if [[ "$TARGET_USER" == "root" ]]; then
      remote_exec "mkdir -p /etc/atlas_user_auth && cp ${TARGET_PATH}/backend/.env.example ${ENV_FILE} && chown root:root ${ENV_FILE} && chmod 640 ${ENV_FILE}"
    else
      remote_exec "sudo mkdir -p /etc/atlas_user_auth && sudo cp ${TARGET_PATH}/backend/.env.example ${ENV_FILE} && sudo chown root:root ${ENV_FILE} && sudo chmod 640 ${ENV_FILE}"
    fi
  fi

  if [[ "$INSTALL_SYSTEMD_UNIT" -eq 1 ]]; then
    if [[ "$ALLOW_INTERACTIVE_SUDO" -ne 1 ]]; then
      echo "--install-systemd-unit requires --allow-interactive-sudo"
      exit 1
    fi
    if [[ "$TARGET_USER" == "root" ]]; then
      remote_exec "cp ${TARGET_PATH}/deploy/atlas_user_auth.service /etc/systemd/system/atlas_user_auth.service && systemctl daemon-reload && systemctl enable atlas_user_auth"
    else
      remote_exec "sudo cp ${TARGET_PATH}/deploy/atlas_user_auth.service /etc/systemd/system/atlas_user_auth.service && sudo systemctl daemon-reload && sudo systemctl enable atlas_user_auth"
    fi
  fi

  if [[ "$INSTALL_NGINX_SITE" -eq 1 ]]; then
    if [[ "$ALLOW_INTERACTIVE_SUDO" -ne 1 ]]; then
      echo "--install-nginx-site requires --allow-interactive-sudo"
      exit 1
    fi
    if [[ "$TARGET_USER" == "root" ]]; then
      remote_exec "cp ${TARGET_PATH}/deploy/nginx-atlas_user_auth.conf /etc/nginx/snippets/nginx-atlas_user_auth.conf && nginx -t && systemctl reload nginx"
    else
      remote_exec "sudo cp ${TARGET_PATH}/deploy/nginx-atlas_user_auth.conf /etc/nginx/snippets/nginx-atlas_user_auth.conf && sudo nginx -t && sudo systemctl reload nginx"
    fi
  fi
fi

if [[ "$ALLOW_INTERACTIVE_SUDO" -eq 1 ]]; then
  if [[ "$TARGET_USER" == "root" ]]; then
    remote_exec "systemctl restart ${SERVICE_NAME}"
  else
    remote_exec "sudo systemctl restart ${SERVICE_NAME}"
  fi
  echo "Health checks..."
  remote_exec "curl -fsS http://127.0.0.1:${PORT}/healthz && curl -fsS http://127.0.0.1:${PORT}/api/healthz"
else
  echo "Skipped service restart (no sudo)."
fi

echo "Deployment completed."
rm -f "$TMP_ARCHIVE"
