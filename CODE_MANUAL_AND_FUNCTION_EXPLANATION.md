# AtlasUserAuth Code Manual and Function Explanation

Last updated: 2026-03-30
Status: Living document (must be updated with each meaningful code change)

## Purpose

This file is the shared programmer manual for AtlasUserAuth.
It explains:

- how the system is structured
- what each module/function is responsible for
- how auth/session/authorization flows work
- what must be updated when behavior changes

If code and this manual ever disagree, update this manual in the same change set.

## Authoritative Requirements

Implementation decisions in this repo are based on:

1. `Auth_prompt.md`
2. `Auth_prompt_minimal.md`
3. `AtlasUserAuth_Deploy_Factsheet.md`

`Atlas_frontend_scaffolding.md` is reference-only and not authoritative.

## System Overview

AtlasUserAuth is a standalone FastAPI service that centralizes:

- identity verification (login/logout/session)
- shared browser session across Atlas apps
- per-app role/rights lookup via `AppKey`
- admin provisioning and access management

Atlas apps remain independent for app logic, but they rely on AtlasUserAuth for trusted user context.

## Design Principles

- Keep implementation simple and auditable.
- Prefer explicit services over hidden framework magic.
- Treat auth failures generically to avoid account enumeration.
- Keep rights scoped per app (`AppKey`) with no cross-app leakage.
- Make deployment repeatable using script + systemd + nginx artifacts.

## Repository Structure (Implemented)

Current implemented layout:

```text
backend/
  app/
    main.py
    core/
      settings.py
      security.py
      logging.py
    db/
      session.py
      models.py
    api/
      deps.py
      routes/
        auth.py
        users.py
        employees.py
        health.py
    schemas/
      auth.py
      users.py
      employees.py
      common.py
    services/
      auth_service.py
      session_service.py
      lockout_service.py
      csrf_service.py
      employee_directory_service.py
      user_access_service.py
      audit_log_service.py
  requirements.txt
  .env.example
migrations/
  001_create_atlas_auth_tables.sql
deploy/
  deploy_to_debian.sh
  check_remote_runtime.sh
  atlas_user_auth.service
  nginx-atlas_user_auth.conf
  deploy.md
```

## Core Runtime Flows

## 1) Login

1. Client sends credentials to `POST /auth/login`.
2. Service checks rate/lockout state by IP and account.
3. Password/PIN hash is verified with PBKDF2-HMAC-SHA256.
4. On success, server creates a session and sets secure HttpOnly cookie.
5. Audit log records success/failure with safe metadata.

## 2) Current User for App

1. Client calls `GET /auth/me?appKey=<app_key>`.
2. Service validates session from cookie.
3. Service resolves access from `dbo.AtlasAppAccess` for that `EmployeeID + AppKey`.
4. Response includes user profile + role + rights for that app only.

## 3) Provision by EmployeeID

1. Admin calls `POST /auth/users/provision-by-employee-id`.
2. Service loads cached employee directory (refresh every 300s).
3. EmployeeID is normalized and validated against directory data.
4. If employee exists, service creates/updates local auth/app-access records.
5. Unknown EmployeeID values are rejected.

## Security Controls Mapping

- Password verification: PBKDF2-HMAC-SHA256
- Session: server-side, signed cookie, HttpOnly, Secure, SameSite configured by env
- CSRF: required for cookie-authenticated state-changing endpoints
- Brute-force protection: per-IP and per-account rate limits + lockout windows
- Validation: Pydantic request/response schemas
- Logging: structured auth audit events
- Secrets: environment variables only

## Database Model Summary

- Existing: `dbo.AtlasUsers` for credentials and identity
- New: `dbo.AtlasAppAccess`
  - `EmployeeID`
  - `AppKey`
  - `Role`
  - `RightsJson`
  - `IsActive`
  - `CreatedAt`
  - `UpdatedAt`
  - unique index on (`EmployeeID`, `AppKey`)

## Endpoint Contract Summary

Minimum endpoint set:

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me?appKey={appKey}`
- `GET /auth/users` (admin)
- `PUT /auth/users/{employeeId}/apps/{appKey}` (admin)
- `POST /auth/users/{employeeId}/reset-credential` (admin)
- `POST /auth/users/provision-by-employee-id` (admin)
- `GET /auth/employees/search?q=...` (admin helper)
- `GET /healthz`
- `GET /api/healthz`

Frontend pages:

- `GET /` login page
- `GET /admin` admin rights-management page

## Deployment Summary

Target Debian deployment standard:

- App path: `/home/rune/dev/atlas_user_auth`
- Env file: `/etc/atlas_user_auth/atlas_user_auth.env`
- systemd service: `atlas_user_auth`
- Internal port: `5020`
- nginx public route: `/atlas_user_auth/`

Required deploy artifacts must ship with backend code.

## Developer Workflow Rule (Manual Maintenance)

For every PR or local change:

1. Update code.
2. Update this manual in the same change if behavior, config, schema, routes, or structure changed.
3. Update `Last updated` date at top.
4. Add a short entry to the changelog section below.

## Changelog (Manual)

- 2026-03-29: Created initial manual structure and baseline architecture/function guidance.
- 2026-03-30: Implemented FastAPI backend skeleton, auth/session APIs, admin APIs, login/admin frontend pages, SQL migrations, env example, and deploy artifacts.
- 2026-03-30: Added local developer run + smoke scripts and a complete DrawingExtractor auth rewrite guide for programmers/AI agents.
- 2026-03-30: Added generic Atlas app auth integration guide template for reuse across all apps.
- 2026-03-30: Added one-page quickstart checklist for sprint planning and rapid onboarding.

## Function and Module Explanations

Module: `backend/app/main.py`
- `app`: FastAPI application instance and route registration point.
- `login_page(request)`: Serves shared login UI (`/`).
- `admin_page(request)`: Serves admin UI (`/admin`).

Module: `backend/app/api/routes/auth.py`
- `login(payload, request, response, db, settings)`: validates credentials, enforces lockout, creates session, sets auth + CSRF cookies.
- `logout(request, response, db, settings, session, session_cookie)`: enforces CSRF, destroys server session, clears cookies.
- `me(appKey, db, settings, session)`: returns authenticated identity + app-scoped role/rights.

Module: `backend/app/api/routes/users.py`
- `list_auth_users(...)`: admin-only user listing.
- `upsert_user_access(...)`: admin-only role/rights write for one `EmployeeID + AppKey`.
- `reset_user_credential(...)`: admin-only password reset.
- `provision_by_employee_id(...)`: admin-only provisioning with required employee-directory validation.

Module: `backend/app/api/routes/employees.py`
- `employee_search(q, ...)`: admin-only cached employee directory lookup.

Module: `backend/app/api/routes/health.py`
- `healthz()`: liveness endpoint.
- `api_healthz(db)`: API health including DB probe and directory-cache diagnostics.

Module: `backend/app/services/auth_service.py`
- `normalize_employee_id(value)`: canonical numeric normalization (`\"00123\" -> \"123\"`).
- `verify_credentials(...)`: AtlasUsers or break-glass admin verification.
- `reset_credential(...)`: PBKDF2-based password reset.

Module: `backend/app/services/session_service.py`
- `create_session(...)`: creates server-side session row and signed cookie token.
- `get_session(...)`: validates signature, idle/absolute timeout, refreshes last-seen.
- `destroy_session(...)`: deletes session row by signed cookie.

Module: `backend/app/services/employee_directory_service.py`
- `refresh_cache(settings)`: pulls `/Employees/all` and refreshes in-memory cache.
- `search_employees(settings, q, limit)`: text lookup over cached directory.
- `get_employee(settings, employee_id)`: exact employee lookup for provisioning.
- `cache_status()`: cache diagnostics for `/api/healthz`.

Module: `backend/app/services/lockout_service.py`
- `is_locked(ip, account)`: checks active lockout state.
- `register_failure(ip, account)`: records failed attempts and sets lockouts.
- `register_success(ip, account)`: clears counters/lockouts on success.

Module: `backend/app/services/csrf_service.py`
- `enforce_csrf(request, expected, header_name)`: blocks state-changing requests without matching CSRF token.

Module: `backend/app/services/user_access_service.py`
- `list_users(...)`: returns AtlasUsers summary source.
- `get_app_access(...)`: returns active app-specific access row.
- `upsert_app_access(...)`: creates or updates role/rights per app.

Module: `backend/app/services/audit_log_service.py`
- `log_event(...)`: structured auth/admin audit logging helper.

## Deploy Artifacts

Implemented in `deploy/`:

- `deploy_to_debian.sh`
- `check_remote_runtime.sh`
- `atlas_user_auth.service`
- `nginx-atlas_user_auth.conf`
- `deploy.md`

## Local Development Artifacts

- `backend/scripts/run_local.sh`: creates local venv, installs requirements, creates `.env.local`, starts uvicorn.
- `backend/scripts/smoke_test_local.sh`: checks login/admin pages and health endpoints.
- `backend/LOCAL_DEVELOPMENT.md`: local setup + smoke instructions.

## Client App Migration Guides

- `docs/DRAWING_EXTRACTOR_AUTH_REWRITE_GUIDE.md` is the canonical rewrite blueprint for moving DrawingExtractor (and similar apps) to AtlasUserAuth.
- `docs/ATLAS_APP_AUTH_INTEGRATION_GUIDE.md` is the app-agnostic integration standard/template for any Atlas app.
- `docs/ATLAS_AUTH_QUICKSTART_ONE_PAGER.md` is the condensed rollout checklist for planners and implementers.
- It includes:
  - endpoint mapping
  - frontend/backend rewrite steps
  - CSRF/cookie handling contract
  - legacy code removal checklist
  - rollout/testing matrix
  - copy-paste AI agent prompt

## Verification Notes

Local checks run:

- Python syntax compile: passed (`python3 -m compileall backend/app`).
- Shell script syntax checks: passed (`bash -n deploy/*.sh`).
- Local runtime boot: passed via `backend/scripts/run_local.sh`.
- Local smoke test: passed via `backend/scripts/smoke_test_local.sh` for `/`, `/admin`, `/healthz`, `/api/healthz`.

## Function-by-Function Section Template

Use this template whenever new functions/classes are introduced:

```text
Module: app/services/auth_service.py
Function: verify_credentials(employee_id: str, password: str) -> AuthResult
Purpose: Validates provided credentials against AtlasUsers with secure hash verification.
Inputs: employee_id, password
Output: AuthResult (success/failure + normalized user context)
Side effects: emits audit log events; increments failure counters on invalid auth
Failure modes: generic invalid credentials, lockout active, DB unavailability
Security notes: never returns whether user exists; timing-safe compare for hash
```

This section should become the primary quick-reference for programmers as implementation expands.
