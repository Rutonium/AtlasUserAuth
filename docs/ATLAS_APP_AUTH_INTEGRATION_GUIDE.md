# Atlas App Integration Guide: Standardizing on AtlasUserAuth

Last updated: 2026-03-30
Audience: Atlas developers and AI coding agents
Scope: Any Atlas application migrating from local auth to shared AtlasUserAuth

## 1. Objective

Use AtlasUserAuth as the single authentication authority across Atlas apps while keeping authorization app-specific.

Target outcomes:

- one login across apps
- shared browser session
- rights isolation per app via `appKey`
- no duplicated login/security logic in each app

## 2. Required Integration Contract

Every integrated app must follow this contract:

1. Credentials are verified only by AtlasUserAuth.
2. Current user context is resolved only by `GET /api/auth/me?appKey=<app_key>`.
3. App-side authorization uses `role` and `rights` from AtlasUserAuth response.
4. App key is server-configured and never user-editable.
5. State-changing auth calls include CSRF header from `atlas_auth_csrf` cookie.

## 3. Standard Endpoints

AtlasUserAuth endpoints used by all apps:

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me?appKey=<app_key>`

Admin/ops endpoints (optional for app runtime):

- `GET /api/auth/users`
- `PUT /api/auth/users/{employeeId}/apps/{appKey}`
- `POST /api/auth/users/provision-by-employee-id`
- `GET /api/auth/employees/search?q=...`

## 4. App Configuration Template

Add these variables to each client app:

```env
ATLAS_AUTH_BASE_URL=https://atlas.subcpartner.com/atlas_user_auth
ATLAS_AUTH_APP_KEY=<replace_with_app_key>
ATLAS_AUTH_TIMEOUT_SECONDS=10
ATLAS_AUTH_LOGIN_PATH=/api/auth/login
ATLAS_AUTH_LOGOUT_PATH=/api/auth/logout
ATLAS_AUTH_ME_PATH=/api/auth/me
USE_ATLAS_AUTH=true
```

`ATLAS_AUTH_APP_KEY` examples:

- `drawing_extractor`
- `asset_management`
- `people_planner`

## 5. Integration Modes

## A) Direct browser-to-AtlasUserAuth (recommended)

- Frontend directly calls AtlasUserAuth.
- Simplest implementation and least backend glue code.

Required:

- shared parent domain
- AtlasUserAuth CORS includes app origin
- cookie scope/path configured for cross-app session behavior

## B) Backend proxy mode

- App backend exposes local `/api/auth/*` and proxies to AtlasUserAuth.
- Useful when frontend cannot call cross-service endpoints directly.

Proxy must forward:

- request body
- cookie headers
- `Set-Cookie`
- CSRF header
- status codes and response bodies transparently

## 6. Frontend Implementation Pattern

## 6.1 Login flow

- Submit credentials to AtlasUserAuth login endpoint.
- Use `credentials: include`.
- On success, navigate to app home.
- On failure, show generic message.

## 6.2 Session bootstrap

On app init and protected-route entry:

- call `/api/auth/me?appKey=<app_key>`
- if unauthenticated, route to login
- if authenticated, hydrate app auth store with:
  - `employee_id`
  - `name`
  - `is_admin`
  - `role`
  - `rights`

## 6.3 Logout flow

- read `atlas_auth_csrf` cookie
- send `X-CSRF-Token` header
- call logout endpoint with cookies
- clear local auth state
- redirect to login/public page

## 7. Backend Implementation Pattern (App Side)

If app backend enforces server-side permissions:

1. Resolve user context from AtlasUserAuth using incoming auth cookie.
2. Cache request-local identity only (no long-lived trust cache unless explicitly designed).
3. Use returned `rights` and `role` for route guards.
4. Deny by default when auth service unavailable or rights missing.

## 8. Authorization Model Pattern

Use common helpers in each app:

```text
can(right_key: str) -> bool
has_role(role_name: str) -> bool
is_admin() -> bool
```

Rules:

- default false when key absent
- never infer rights from UI state
- never trust user-provided role/right payloads

## 9. Legacy Auth Decommission Checklist

Remove from app codebase:

- local credential verification
- local password hashing/reset logic
- local auth lockout/rate-limit duplication
- local session generation/parsing
- local auth DB tables no longer needed

Keep only:

- AtlasUserAuth integration client/proxy
- app authorization guards

## 10. Shared Nginx/Deployment Requirements

On shared host:

- keep app and AtlasUserAuth under same parent domain
- app path example: `/my_app/`
- auth path: `/atlas_user_auth/`
- ensure forwarded headers are set properly

Cookie/session checks:

- `HttpOnly`
- `Secure` (prod)
- `SameSite` per deployment strategy
- domain/path allow intended cross-app behavior

## 11. Test Matrix for Any App Migration

## Functional

1. Login once, open second integrated app, user remains authenticated.
2. `/auth/me` returns app-specific rights for each app key.
3. Logout from one app ends session for all integrated apps in browser.

## Authorization

1. User with rights in app A but not B is denied in app B.
2. Role/rights change in AtlasUserAuth admin is reflected in app behavior.
3. Missing rights key defaults to denied behavior.

## Security

1. CSRF missing on state-changing auth request returns `403`.
2. Cookie flags validated in browser tools.
3. Local app endpoints do not accept fake user identities.

## Resilience

1. AtlasUserAuth outage produces controlled fail-closed behavior for protected routes.
2. Expired session returns user to login flow cleanly.

## 12. Rollout Pattern (Per App)

1. Add feature flag `USE_ATLAS_AUTH`.
2. Implement integration behind flag.
3. QA in staging with representative users/rights.
4. Provision rights in AtlasUserAuth admin.
5. Enable in production.
6. Observe and then remove old auth code.

## 13. Reusable App Migration Template

Copy and fill before implementation:

```text
App Name:
App Key:
Current Auth Mode: local / mixed / external
Integration Mode: direct / backend-proxy
Frontend Entry Points:
Backend Auth Endpoints to Remove:
Authorization Guard Locations:
Required Rights Keys:
Feature Flag Name:
Staging Test Owner:
Production Rollout Date:
Rollback Trigger:
```

## 14. AI Agent Prompt (Generic)

```text
Integrate <APP_NAME> with AtlasUserAuth using appKey=<APP_KEY>.

Use only AtlasUserAuth for login/logout/me.
Do not keep local credential verification/session creation logic.

Requirements:
- Include cookies on auth requests
- Send X-CSRF-Token from atlas_auth_csrf cookie for state-changing requests
- Use /auth/me response as the only trusted identity/rights source
- Keep authorization app-specific using returned role/rights
- Remove legacy local auth code paths
- Add tests for session bootstrap, unauthorized access, and rights enforcement
- Gate rollout behind feature flag USE_ATLAS_AUTH

Deliver:
1) files changed
2) old->new endpoint mapping
3) tests added
4) rollout and rollback steps
```
