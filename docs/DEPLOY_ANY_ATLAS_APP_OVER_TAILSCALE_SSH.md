# Deploy Any Atlas App Over Tailscale SSH

Last updated: 2026-04-05  
Audience: Codex, developers, and operators deploying Atlas apps to the Debian sandbox/server estate

## Purpose

This is the reusable deployment standard to copy into other Atlas app repos.

It is based on what was confirmed while deploying AtlasUserAuth and should be treated as the preferred pattern for:

- `AssetManagement`
- `PeoplePlanner`
- future Atlas apps on the same server model

## Core Principle

Do not treat the server like a development clone.

Preferred pattern:

- local machine is the real Git repo connected to GitHub
- GitHub is the source of truth
- server receives a deployed file bundle or archive
- service runs under the correct app runtime user
- transport happens over Tailscale SSH

This avoids:

- accidental `git pull` surprises on the server
- mixed ownership problems
- hidden drift from manual server edits

## Current Confirmed Deployment Reality

These facts were verified live on `runes-sandkasse`:

- remote host name: `runes-sandkasse`
- remote access method: `tailscale ssh`
- normal SSH is not the standard path
- deploy transport user: `root`
- runtime owner for AtlasUserAuth: `rune`
- nginx is already used as reverse proxy
- systemd is already used for service control

Use this exact connectivity test first:

```bash
tailscale ssh root@runes-sandkasse
```

If Tailscale asks for browser authorization, complete it before any deploy attempt.

## Mandatory Deployment Standards For New Atlas Apps

Every Atlas app repo should include deploy artifacts in the repo itself:

1. deploy script
2. remote runtime check script
3. systemd unit template
4. nginx config or nginx include snippet
5. deploy documentation

Do not rely on memory or hand-written shell snippets only.

## Generic Environment Variables For Deploy Scripts

Adopt variables in this shape:

```bash
export ATLAS_DEPLOY_HOST=runes-sandkasse
export ATLAS_DEPLOY_USER=root
export ATLAS_SSH_MODE=tailscale
export ATLAS_DEPLOY_PATH=/home/<runtime_user>/dev/<repo_name>
export ATLAS_APP_OWNER=<runtime_user>
```

Example for `AssetManagement` if it runs as user `rune`:

```bash
export ATLAS_DEPLOY_HOST=runes-sandkasse
export ATLAS_DEPLOY_USER=root
export ATLAS_SSH_MODE=tailscale
export ATLAS_DEPLOY_PATH=/home/rune/dev/asset_management
export ATLAS_APP_OWNER=rune
```

Example for `PeoplePlanner` if it runs as user `rune`:

```bash
export ATLAS_DEPLOY_HOST=runes-sandkasse
export ATLAS_DEPLOY_USER=root
export ATLAS_SSH_MODE=tailscale
export ATLAS_DEPLOY_PATH=/home/rune/dev/people_planner
export ATLAS_APP_OWNER=rune
```

## Deploy Script Contract

Each app should have a deploy script similar in principle to AtlasUserAuth’s current deploy flow.

That script should:

- create an archive from the repo
- exclude `.git`, venvs, caches, build outputs, and local DB files
- upload over `tailscale ssh`
- extract to the target path
- fix file ownership back to the runtime user
- install dependencies as the runtime user
- restart the systemd service
- run health checks
- print recent logs on failure

## Remote Runtime Check Contract

Each app should also ship a check script that can:

- confirm Tailscale SSH access
- confirm service/unit presence
- confirm env file presence
- confirm runtime tools are installed
- confirm the internal port is listening
- confirm the public nginx route responds
- show recent logs

## Generic Server Layout Pattern

Unless there is a reason to differ, keep this structure:

- app code: `/home/<runtime_user>/dev/<repo_name>`
- env file: `/etc/<service_name>/<service_name>.env`
- systemd service name: `<service_name>.service`
- nginx snippet: `/etc/nginx/snippets/nginx-<service_name>.conf`

Example:

- repo: `asset_management`
- service: `asset_management`
- env file: `/etc/asset_management/asset_management.env`

## Tailscale SSH Rules

This is important enough to make explicit:

- use `tailscale ssh`, not only plain Tailscale connectivity
- do not assume standard `ssh user@host` is allowed
- do not assume the runtime user is reachable directly
- transport as `root` is acceptable if runtime ownership is restored correctly

## systemd Pattern

Each app should have a unit file that clearly sets:

- `User=<runtime_user>`
- `Group=<runtime_user>`
- `WorkingDirectory=<app_runtime_dir>`
- `EnvironmentFile=<env_file_path>`
- bind address and port
- `Restart=on-failure`

Example expectations:

```ini
[Service]
User=rune
Group=rune
WorkingDirectory=/home/rune/dev/asset_management/backend
EnvironmentFile=/etc/asset_management/asset_management.env
ExecStart=/home/rune/dev/asset_management/backend/.venv/bin/gunicorn ...
Restart=on-failure
```

## nginx Pattern

Prefer route-prefix deployment on the shared nginx host:

- `/atlas_user_auth/`
- `/asset_management/`
- `/people_planner/`

Required nginx behaviors:

- redirect missing trailing slash to the route with slash
- proxy app requests to the local service port
- preserve `Host`, `X-Real-IP`, `X-Forwarded-*`
- set explicit `client_max_body_size`

## Health Check Standard

Every app should expose at least:

- `/healthz`
- `/api/healthz` if there is an API layer

The deploy script should call both when applicable.

It should also verify the public nginx route, not only the internal port.

## Recommended Deployment Sequence

1. verify local git state
2. verify Tailscale is up
3. verify `tailscale ssh root@runes-sandkasse`
4. export deploy variables
5. run remote runtime check
6. deploy archive
7. restart service
8. run health checks
9. verify public route
10. inspect logs if anything looks off

## What To Preserve From The AtlasUserAuth Flow

These parts of the current AtlasUserAuth deploy are worth copying to other apps:

- Tailscale SSH support in the deploy script
- root transport with restored runtime ownership
- script-driven systemd/nginx/env installation flags
- remote health checks after restart
- helpful failure output from `systemctl` and `journalctl`
- explicit deploy environment variables

## What Not To Do

Avoid these patterns:

- editing files manually on the server as the normal workflow
- deploying by `git pull` on the server unless that repo is intentionally managed that way
- leaving files owned by `root` when the service should run as another user
- depending on memory for service names, paths, or ports
- skipping post-deploy verification

## Minimal Checklist For AssetManagement

When preparing AssetManagement deployment, make sure the repo includes:

1. `deploy/deploy_to_debian.sh`
2. `deploy/check_remote_runtime.sh`
3. `deploy/asset_management.service`
4. `deploy/nginx-asset_management.conf`
5. `deploy/deploy.md`

And set:

```bash
export ATLAS_DEPLOY_HOST=runes-sandkasse
export ATLAS_DEPLOY_USER=root
export ATLAS_SSH_MODE=tailscale
export ATLAS_DEPLOY_PATH=/home/rune/dev/asset_management
export ATLAS_APP_OWNER=rune
```

## Minimal Checklist For PeoplePlanner

When preparing PeoplePlanner deployment, make sure the repo includes:

1. `deploy/deploy_to_debian.sh`
2. `deploy/check_remote_runtime.sh`
3. `deploy/people_planner.service`
4. `deploy/nginx-people_planner.conf`
5. `deploy/deploy.md`

And set:

```bash
export ATLAS_DEPLOY_HOST=runes-sandkasse
export ATLAS_DEPLOY_USER=root
export ATLAS_SSH_MODE=tailscale
export ATLAS_DEPLOY_PATH=/home/rune/dev/people_planner
export ATLAS_APP_OWNER=rune
```

## Prompt Template For Codex

Use this at the start of work in another app repo:

```text
Implement a production-ready deploy flow for this Atlas app.

Read these first:
1. docs/DEPLOY_ANY_ATLAS_APP_OVER_TAILSCALE_SSH.md
2. docs/CONNECT_ANY_APP_TO_ATLAS_AUTH_MANUAL.md

Requirements:
- deploy over Tailscale SSH
- assume transport user is root
- restore ownership to the runtime user
- do not rely on git on the server
- include deploy script, runtime check, systemd unit, nginx config, and deploy docs
- run health checks after restart

Return:
1. files created/changed
2. deploy command
3. rollback approach
4. verification checklist
```
