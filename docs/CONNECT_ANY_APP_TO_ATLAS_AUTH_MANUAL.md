# Connect Any App To AtlasUserAuth

Last updated: 2026-04-05  
Audience: Codex, developers, and operators integrating Atlas applications with AtlasUserAuth

## Purpose

Use this manual when connecting an existing Atlas application to shared authentication.

This is the generic integration playbook for:

- `AssetManagement`
- `PeoplePlanner`
- future Atlas apps

The goal is always the same:

- AtlasUserAuth owns login, logout, and session identity
- each app owns only its own business rules
- each app reads app-specific access from AtlasUserAuth using its own `appKey`

## Non-Negotiable Contract

Every integrated app must follow these rules:

1. AtlasUserAuth is the only place that verifies employee credentials.
2. The client app must stop creating its own local authenticated session model.
3. The client app must resolve the current user from `GET /api/auth/me?appKey=<app_key>`.
4. The client app must enforce what users can see or do based on the returned `rights`, `role`, `access_level`, and `access_label`.
5. `appKey` must be a server-configured constant, never user-editable.
6. State-changing auth calls must include the `X-CSRF-Token` header copied from the `atlas_auth_csrf` cookie.

## Current AtlasUserAuth Facts

Treat these as current working assumptions unless infrastructure changes:

- public auth route: `http://139.162.170.26/atlas_user_auth/`
- shared login route: `http://139.162.170.26/atlas_user_auth/login`
- admin route: `http://139.162.170.26/atlas_user_auth/admin`
- app access matrix: `http://139.162.170.26/atlas_user_auth/admin/access-matrix`
- rights-definition matrix: `http://139.162.170.26/atlas_user_auth/admin/rights-matrix`

## App Key Standards

Choose one stable `appKey` per app and do not rename it casually.

Recommended keys:

- `asset_management`
- `people_planner`
- `drawing_extractor`

If a key changes later, all app-access data and any rights definitions tied to that key will need migration.

## AtlasUserAuth Endpoints Used By Apps

Runtime endpoints:

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me?appKey=<app_key>`
- `GET /login?return_to=<urlencoded_app_url_or_path>`

Admin endpoints used by operations:

- `GET /api/auth/users`
- `GET /api/auth/users/summary`
- `GET /api/auth/users/matrix`
- `PUT /api/auth/users/{employeeId}/apps/{appKey}`
- `POST /api/auth/users/provision-by-employee-id`
- `GET /api/auth/employees/search?q=...`
- `POST /api/auth/users/{employeeId}/reset-credential`
- `GET /api/auth/apps/rights-matrix?appKey=<app_key>`

## Required App Configuration

Each app should have variables similar to:

```env
ATLAS_AUTH_BASE_URL=http://139.162.170.26/atlas_user_auth
ATLAS_AUTH_APP_KEY=<replace_with_app_key>
ATLAS_AUTH_TIMEOUT_SECONDS=10
ATLAS_AUTH_LOGIN_PATH=/api/auth/login
ATLAS_AUTH_LOGOUT_PATH=/api/auth/logout
ATLAS_AUTH_ME_PATH=/api/auth/me
USE_ATLAS_AUTH=true
```

Examples:

```env
ATLAS_AUTH_APP_KEY=asset_management
```

```env
ATLAS_AUTH_APP_KEY=people_planner
```

## Integration Modes

### Recommended: direct browser-to-AtlasUserAuth

Use this if the frontend can call AtlasUserAuth directly with cookies.

Benefits:

- less code
- less proxying
- fewer moving parts

Requirements:

- same parent domain or otherwise compatible cookie/CORS setup
- browser requests must use credentials

### Alternative: backend proxy mode

Use this only if the frontend cannot talk to AtlasUserAuth directly.

Proxy rules:

- proxy body through unchanged
- forward `Cookie`
- forward `Set-Cookie`
- forward CSRF header
- preserve status codes
- do not add local auth logic

## Frontend Rewrite Pattern

### Login flow

Preferred pattern:

```js
window.location.href =
  `${ATLAS_AUTH_BASE_URL}/login?return_to=${encodeURIComponent('/your_app_path/')}`;
```

AtlasUserAuth will:

- show the shared login page
- authenticate the user
- redirect them back to the app

### Session bootstrap

On app load and on protected routes:

```text
GET /api/auth/me?appKey=<app_key>
```

Use this as the only trusted identity source.

Expected response shape:

```json
{
  "authenticated": true,
  "employee_id": 10698,
  "name": "Rune Værndal",
  "email": "rv@subcpartner.com",
  "is_admin": true,
  "app_key": "asset_management",
  "role": "user",
  "access_level": 4,
  "access_label": "Manager",
  "rights": {
    "can_view": true,
    "can_edit": true,
    "can_approve": false
  }
}
```

If the response is unauthenticated or `401`:

- clear any local user state
- route to login

### Logout flow

For logout:

1. read the `atlas_auth_csrf` cookie
2. send `X-CSRF-Token`
3. include credentials/cookies
4. clear local app state after success

## Authorization Pattern Inside The App

AtlasUserAuth returns access data. The client app decides what that means in practice.

Example:

- `can_view` means show list page
- `can_edit` means enable edit form
- `can_approve` means show approval controls

That behavior is implemented in the app itself, not inside AtlasUserAuth.

Recommended helpers:

```text
can(right_key) -> boolean
has_role(role_name) -> boolean
level_at_least(n) -> boolean
```

Default behavior:

- missing right key means denied
- missing access means denied
- auth-service failure on protected operations should fail closed

## Access Levels 1-5

AtlasUserAuth now supports a standardized cross-app level system:

1. Viewer
2. Contributor
3. Specialist
4. Manager
5. Owner

Use this for:

- fast assignment in the Access Matrix
- consistent reporting across apps
- a shared language for administrators

Important:

- an app does not have to use all five levels
- a level only becomes meaningful to an app when the app chooses how to interpret it or when its rights matrix defines what the level includes

## Rights Definition Pattern

The admin team can now define rights per app in the Rights Matrix page:

- one app at a time
- rows are right keys
- columns are levels `1-5`
- checked cells mean that level includes that right

Example for `people_planner`:

- `can_view_schedule`
- `can_edit_schedule`
- `can_assign_personnel`
- `can_publish_plan`

The app should still read the resolved `rights` payload and enforce behavior on its own side.

## AssetManagement Integration Checklist

Use this when starting `AssetManagement`:

### Suggested app key

- `asset_management`

### Codex task framing

1. identify and remove local login logic
2. identify local session storage or token generation
3. replace login entry with redirect to AtlasUserAuth
4. add bootstrap call to `/api/auth/me?appKey=asset_management`
5. move permissions to helpers based on AtlasUserAuth response
6. add feature flag `USE_ATLAS_AUTH`
7. test shared login/logout with AtlasUserAuth

### Rights planning starter

Possible rights to discuss:

- `can_view_assets`
- `can_create_assets`
- `can_edit_assets`
- `can_archive_assets`
- `can_admin_assets`

## PeoplePlanner Integration Checklist

Use this when starting `PeoplePlanner`:

### Suggested app key

- `people_planner`

### Codex task framing

1. identify and remove local login logic
2. replace app login route with redirect to AtlasUserAuth
3. bootstrap auth state from `/api/auth/me?appKey=people_planner`
4. refactor schedule/planning permissions to use Atlas rights helpers
5. add feature flag `USE_ATLAS_AUTH`
6. test login redirect, shared session, and logout

### Rights planning starter

Possible rights to discuss:

- `can_view_schedule`
- `can_edit_schedule`
- `can_assign_personnel`
- `can_lock_schedule`
- `can_admin_people_planner`

## Rollout Pattern For Any App

1. add `USE_ATLAS_AUTH=false`
2. implement the AtlasUserAuth path behind the flag
3. keep legacy auth temporarily while QA runs
4. create the new app key in AtlasUserAuth by assigning access in admin
5. define rights in the Rights Matrix page
6. provision representative users
7. switch the app to `USE_ATLAS_AUTH=true`
8. monitor behavior
9. remove legacy auth code after soak period

## Test Checklist

### Functional

1. login via AtlasUserAuth returns to app
2. refreshing the app keeps the user signed in
3. opening another integrated app reuses the same session
4. logout clears the session for all integrated apps in that browser

### Authorization

1. a user with no access for the app is denied
2. a user with level 1 gets the expected minimum behavior
3. changing rights in AtlasUserAuth changes app behavior
4. missing right key behaves as deny

### Security

1. no local password verification remains in the app
2. no local session minting remains in the app
3. CSRF is present on logout and other state-changing auth calls

## Prompt Template For Codex

Use this as the first message when asking Codex to connect a new app:

```text
Integrate <APP_NAME> with AtlasUserAuth.

Read these documents first:
1. docs/CONNECT_ANY_APP_TO_ATLAS_AUTH_MANUAL.md
2. docs/DEPLOY_ANY_ATLAS_APP_OVER_TAILSCALE_SSH.md

App details:
- App name: <APP_NAME>
- App key: <APP_KEY>
- Runtime path/URL prefix: <APP_PATH>
- Feature flag: USE_ATLAS_AUTH

Requirements:
- remove local credential verification
- remove local session creation logic
- use AtlasUserAuth for login/logout/me only
- enforce permissions from AtlasUserAuth response
- preserve existing business logic
- implement deploy artifacts in the same change set

Also produce:
1. integration summary
2. changed files
3. deploy command
4. test checklist for this app
```
