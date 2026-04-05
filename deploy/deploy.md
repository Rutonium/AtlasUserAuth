# AtlasUserAuth Deployment (Debian)

## One-command deploy

```bash
export ATLAS_DEPLOY_HOST=runes-sandkasse
export ATLAS_DEPLOY_USER=root
export ATLAS_SSH_MODE=tailscale
export ATLAS_DEPLOY_PATH=/home/rune/dev/atlas_user_auth
export ATLAS_APP_OWNER=rune

./deploy/deploy_to_debian.sh \
  --allow-interactive-auth \
  --allow-interactive-sudo
```

Optional first-time infra install:

```bash
export ATLAS_DEPLOY_HOST=runes-sandkasse
export ATLAS_DEPLOY_USER=root
export ATLAS_SSH_MODE=tailscale
export ATLAS_DEPLOY_PATH=/home/rune/dev/atlas_user_auth
export ATLAS_APP_OWNER=rune

./deploy/deploy_to_debian.sh \
  --allow-interactive-auth \
  --allow-interactive-sudo \
  --allow-shared-file-changes \
  --install-env-file \
  --install-systemd-unit \
  --install-nginx-site
```

## Required environment file

- `/etc/atlas_user_auth/atlas_user_auth.env`
- Start with `backend/.env.example` and fill secrets.
- On `runes-sandkasse`, the service runs as user `rune` from `/home/rune/dev/atlas_user_auth/backend`, even when deployment transport is performed as `root` over Tailscale SSH.

## Post-deploy checks

```bash
export ATLAS_DEPLOY_HOST=runes-sandkasse
export ATLAS_DEPLOY_USER=root
export ATLAS_SSH_MODE=tailscale
./deploy/check_remote_runtime.sh
```

Manual checks:

```bash
curl -fsS http://127.0.0.1:5020/healthz
curl -fsS http://127.0.0.1:5020/api/healthz
```

## nginx wiring

Include `deploy/nginx-atlas_user_auth.conf` inside your shared nginx server block.
This exposes the app under `/atlas_user_auth/` and proxies to `127.0.0.1:5020`.
It also adds friendly login aliases:

- `/login` -> `/atlas_user_auth/login`
- `/Login` -> `/atlas_user_auth/login`
