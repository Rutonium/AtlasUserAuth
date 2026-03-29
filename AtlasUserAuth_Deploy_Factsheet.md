# AtlasUserAuth Deploy Factsheet

Practical deployment standard for the new standalone `AtlasUserAuth` service on your Debian host.

Last updated: March 29, 2026.

## Objective

Deploy `AtlasUserAuth` with one script-driven workflow and avoid manual service/nginx/env handling.

## Server Assumptions

- Host: Debian Linux
- Reverse proxy: nginx
- Service manager: systemd
- Runtime user: `rune`
- Repo base: `/home/rune/dev/atlas_user_auth`
- SQL Server backend via `mssql+pyodbc`

## Recommended Runtime Paths

- App code: `/home/rune/dev/atlas_user_auth`
- Env file: `/etc/atlas_user_auth/atlas_user_auth.env`
- Service name: `atlas_user_auth`
- Internal app port: `5020`
- Public route via nginx: `/atlas_user_auth/`

## Non-Negotiable Deploy Artifacts

Every release should include:

1. `deploy/deploy_to_debian.sh`
2. `deploy/check_remote_runtime.sh`
3. `deploy/atlas_user_auth.service`
4. `deploy/nginx-atlas_user_auth.conf`
5. `deploy/deploy.md`

## One-Command Deploy Contract

Primary deploy command should support:

```bash
./deploy/deploy_to_debian.sh \
  --allow-interactive-auth \
  --allow-interactive-sudo
```

And optional infrastructure install flags:

```bash
./deploy/deploy_to_debian.sh \
  --allow-interactive-auth \
  --allow-interactive-sudo \
  --allow-shared-file-changes \
  --install-env-file \
  --install-systemd-unit \
  --install-nginx-site
```

## Script Requirements

`deploy_to_debian.sh` should:

- Archive and upload repo to target host
- Exclude heavy/local artifacts (`.git`, venv, node_modules, dist, caches)
- Extract into `/home/rune/dev/atlas_user_auth`
- Create/update backend venv and install requirements
- Restart systemd service
- Run health checks (`/healthz`, `/api/healthz`)
- Print recent `systemctl`/`journalctl` on failure
- Optionally install env/systemd/nginx artifacts via explicit flags only

`check_remote_runtime.sh` should:

- Validate `systemctl status atlas_user_auth`
- Validate env file presence
- Validate runtime tools (`python3`, `pip`, ODBC dependencies if needed)
- Probe DB host connectivity (best effort)
- Call local health endpoints
- Show recent service logs

## Environment File Standard

File: `/etc/atlas_user_auth/atlas_user_auth.env`

Minimum keys:

```env
ATLAS_AUTH_DB_URL=mssql+pyodbc://user:pass@server/AssetManagement?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes
ATLAS_AUTH_PORT=5020
SESSION_SIGNING_SECRET=replace-with-long-random-secret
LOCAL_ADMIN_PASSWORD=replace-with-break-glass-secret

CORS_ALLOW_ORIGINS=https://your-atlas-host
CORS_ALLOW_CREDENTIALS=true

EMPLOYEE_API_BASE_URL=http://common.subcpartner.com
EMPLOYEE_API_TOKEN=replace-with-local-secret
EMPLOYEE_API_AUTH_HEADER=Authorization
EMPLOYEE_API_AUTH_SCHEME=

AUTH_ATTEMPT_WINDOW_SECONDS=300
AUTH_MAX_ATTEMPTS_PER_IP=50
AUTH_MAX_ATTEMPTS_PER_ACCOUNT=8
AUTH_LOCKOUT_SECONDS=900
```

## systemd Unit Standard

Service file: `deploy/atlas_user_auth.service`

Required behavior:

- `WorkingDirectory=/home/rune/dev/atlas_user_auth/backend`
- `EnvironmentFile=/etc/atlas_user_auth/atlas_user_auth.env`
- Start with gunicorn + uvicorn worker
- `Restart=on-failure`
- fixed bind port `0.0.0.0:5020`

## nginx Standard

Expose app behind a route prefix:

- `/atlas_user_auth/` (frontend/admin UI if any)
- `/atlas_user_auth/api/` -> proxy to `127.0.0.1:5020`

Also include:

- redirect from `/atlas_user_auth` to `/atlas_user_auth/`
- `client_max_body_size` explicitly set
- forwarded headers (`Host`, `X-Real-IP`, `X-Forwarded-*`)

On shared host, prefer integrating locations into shared server block instead of creating conflicting standalone server blocks.

## Release Checklist

Before deploy:

1. Update code and migrations
2. Verify `.env.example` includes new required keys
3. Ensure deploy scripts and unit/nginx templates are in sync

After deploy:

1. `curl -fsS http://127.0.0.1:5020/healthz`
2. `curl -fsS http://127.0.0.1:5020/api/healthz`
3. Verify route via nginx public path
4. Verify login, `/auth/me`, and employee search/provisioning

## Fast Troubleshooting

- Service fails to start: inspect `journalctl -u atlas_user_auth -n 120 --no-pager`
- DB errors: verify connection string + SQL Server reachability
- Employee directory issues: verify `EMPLOYEE_API_*` variables and token
- Cross-app session not shared: verify cookie domain/path/samesite/secure and nginx forwarding

## Recommendation For Codex Prompting

When generating AtlasUserAuth, always require Codex to deliver deploy artifacts in the same PR/change set as backend code:

- deploy scripts
- systemd unit
- nginx config
- deploy docs

This prevents manual deployment drift and keeps releases repeatable.

## Copy-Paste: First Codex Message

Use this as your first message when starting the `AtlasUserAuth` project:

```text
Build a standalone AtlasUserAuth service in this repository.

Read and follow these documents in order:
1) Auth_prompt.md
2) Auth_prompt_minimal.md
3) AtlasUserAuth_Deploy_Factsheet.md

Hard requirements:
- Python FastAPI backend in Atlas-style layout
- SQL Server via mssql+pyodbc
- Shared login/session across Atlas apps
- Per-app independent rights using AppKey
- Employee provisioning must validate against employee API before creating access
- Deliver deploy artifacts in same change set:
  - deploy/deploy_to_debian.sh
  - deploy/check_remote_runtime.sh
  - deploy/atlas_user_auth.service
  - deploy/nginx-atlas_user_auth.conf
  - deploy/deploy.md
- Include SQL migration scripts and .env.example
- Include health endpoints and remote runtime checks

Do not stop at planning. Implement end-to-end, then summarize:
1) Architecture implemented
2) Files created/changed
3) How to deploy with one command
4) How DrawingExtractor should integrate first
```
