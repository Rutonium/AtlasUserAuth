# AtlasUserAuth Deployment (Debian)

## One-command deploy

```bash
./deploy/deploy_to_debian.sh \
  --allow-interactive-auth \
  --allow-interactive-sudo
```

Optional first-time infra install:

```bash
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

## Post-deploy checks

```bash
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
