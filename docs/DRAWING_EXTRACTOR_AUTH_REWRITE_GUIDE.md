# DrawingExtractor Rewrite Guide: Move Authentication to AtlasUserAuth

Last updated: 2026-03-30
Audience: Programmers and AI coding agents

## 1. Goal

Replace DrawingExtractor local authentication with AtlasUserAuth so that:

- login is shared across Atlas apps
- session is remembered across apps in same browser
- authorization remains app-specific via `appKey=drawing_extractor`

## 2. Non-negotiable integration contract

DrawingExtractor must stop owning:

- credential verification
- session creation rules
- local auth lockout logic
- local login/logout identity storage

DrawingExtractor must own only:

- app-local business logic
- app-local authorization checks based on rights returned by AtlasUserAuth

## 3. AtlasUserAuth endpoints to use

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me?appKey=drawing_extractor`
- `GET /login?return_to=<urlencoded_drawingextractor_path>`

Admin-only endpoints for operations team (outside DrawingExtractor runtime UI):

- `GET /api/auth/users`
- `PUT /api/auth/users/{employeeId}/apps/{appKey}`
- `POST /api/auth/users/provision-by-employee-id`
- `GET /api/auth/employees/search?q=...`
- `POST /api/auth/users/{employeeId}/reset-credential`

## 4. Configuration required in DrawingExtractor

Add environment variables:

```env
ATLAS_AUTH_BASE_URL=https://atlas.subcpartner.com/atlas_user_auth
ATLAS_AUTH_APP_KEY=drawing_extractor
ATLAS_AUTH_TIMEOUT_SECONDS=10
ATLAS_AUTH_LOGIN_PATH=/api/auth/login
ATLAS_AUTH_LOGOUT_PATH=/api/auth/logout
ATLAS_AUTH_ME_PATH=/api/auth/me
```

Rules:

- `ATLAS_AUTH_APP_KEY` is server-side config only, never user-editable.
- All auth calls must send/accept cookies (`credentials: include` in browser, cookie-forwarding in backend proxy).

## 5. Frontend rewrite steps (DrawingExtractor)

## 5.1 Replace login entry target

Current pattern (to remove):

- `POST /api/auth/login` against DrawingExtractor local backend

New pattern:

- redirect to AtlasUserAuth login page with return target:

`window.location.href = ${ATLAS_AUTH_BASE_URL}/login?return_to=${encodeURIComponent('/drawing_extractor/')}`

What AtlasUserAuth does:

- shows shared login UI
- authenticates user
- redirects back to `return_to`

Optional (if you keep an in-app login form):

- `POST ${ATLAS_AUTH_BASE_URL}/api/auth/login` with body:

```json
{
  "employee_id": "123",
  "password": "secret"
}
```

Browser request requirements:

- `credentials: "include"`
- `Content-Type: application/json`

Success action (programmatic mode only):

- redirect to DrawingExtractor app root/dashboard

## 5.2 Replace session bootstrap

On app load, call:

`GET ${ATLAS_AUTH_BASE_URL}/api/auth/me?appKey=drawing_extractor` with `credentials: include`

Use response as the only trusted user context source.

Expected shape:

```json
{
  "authenticated": true,
  "employee_id": 123,
  "name": "Jane Doe",
  "email": "jane@company.com",
  "is_admin": false,
  "app_key": "drawing_extractor",
  "role": "user",
  "rights": {
    "can_extract": true,
    "can_review": false
  }
}
```

If `401` or `authenticated=false`:

- clear local UI user state
- route to login view

## 5.3 Replace logout

Call:

`POST ${ATLAS_AUTH_BASE_URL}/api/auth/logout` with:

- `credentials: include`
- CSRF header `X-CSRF-Token` from `atlas_auth_csrf` cookie

Then clear local app state and route to login page.

## 6. Backend rewrite steps (DrawingExtractor)

Choose one approach; prefer A for simplicity.

## A) Frontend direct calls to AtlasUserAuth (recommended)

- DrawingExtractor backend no longer exposes auth endpoints.
- Frontend calls AtlasUserAuth directly.

Requirements:

- shared cookie domain/path configured in AtlasUserAuth
- CORS allowed origin configured in AtlasUserAuth

## B) Backend-for-frontend auth proxy (alternative)

- DrawingExtractor backend keeps `/api/auth/*` but only proxies to AtlasUserAuth.
- No local credential logic allowed.
- Proxy must forward:
  - request body
  - `Cookie`
  - `Set-Cookie`
  - CSRF header

## 7. Authorization rewrite in DrawingExtractor

Replace local role tables/claims parsing with rights from `/auth/me`.

Implementation pattern:

1. Resolve user context once at app boot and on protected-route entry.
2. Store `role` and `rights` in app auth store.
3. Add small helper guards:

```text
can("can_extract") -> boolean
hasRole("admin") -> boolean
```

4. Guard UI actions and backend route execution using these helpers.

Critical rule:

- Never trust role/rights from client-edited payloads.
- Always derive from trusted AtlasUserAuth response tied to cookie session.

## 8. Existing code removal checklist in DrawingExtractor

Delete or disable:

- password hash verification module
- local session/token generator
- local login lockout counters
- local auth DB tables if no longer used
- stale `/api/auth/login|logout|me` handlers with local logic

Keep only:

- optional thin proxy (if using approach B)
- authorization gates consuming AtlasUserAuth context

## 9. CSRF and cookie handling details

For state-changing calls to AtlasUserAuth (`POST`, `PUT`, etc.):

1. Read `atlas_auth_csrf` cookie value.
2. Send header `X-CSRF-Token: <cookie_value>`.
3. Include browser credentials/cookies.

If missing or mismatch:

- AtlasUserAuth returns `403`.

## 10. nginx routing on shared host

Expose AtlasUserAuth path under same parent domain as DrawingExtractor (required for shared session behavior):

- DrawingExtractor: `/drawing_extractor/`
- AtlasUserAuth: `/atlas_user_auth/`

Ensure forwarding headers and cookie scope are compatible.

## 11. Testing matrix for rewrite

## Functional

1. Login once through AtlasUserAuth, open DrawingExtractor, user is already authenticated.
2. Call `/auth/me?appKey=drawing_extractor`, verify role/rights loaded.
3. Logout from DrawingExtractor, session cleared across apps.
4. Redirect to `${ATLAS_AUTH_BASE_URL}/login?return_to=...` returns user to DrawingExtractor after successful login.

## Authorization

1. User with no `drawing_extractor` access gets denied.
2. Rights change in AtlasUserAuth admin page takes effect in DrawingExtractor.
3. Admin/non-admin UI visibility in DrawingExtractor follows returned rights.

## Security

1. Invalid login always returns generic failure message.
2. Missing CSRF header on logout returns `403`.
3. Cookie flags verified (`HttpOnly`, `Secure`, `SameSite`) in browser dev tools.

## Resilience

1. AtlasUserAuth temporarily unavailable: DrawingExtractor shows friendly auth unavailable page and blocks protected actions.
2. Expired session redirects to login cleanly.

## 12. Rollout plan (safe migration)

1. Introduce feature flag in DrawingExtractor:
   - `USE_ATLAS_AUTH=true|false`
2. Implement Atlas path while keeping old path behind flag.
3. Run QA with `true` in staging.
4. Provision all required users/rights in AtlasUserAuth.
5. Cut production to `true`.
6. After soak period, remove old local auth code permanently.

## 13. AI Agent implementation prompt (copy/paste)

```text
Rewrite DrawingExtractor authentication to use AtlasUserAuth.

Do not implement local credential/session logic.
Use only:
- POST {ATLAS_AUTH_BASE_URL}/api/auth/login
- POST {ATLAS_AUTH_BASE_URL}/api/auth/logout
- GET {ATLAS_AUTH_BASE_URL}/api/auth/me?appKey=drawing_extractor

Requirements:
- Keep app-specific authorization from role/rights returned by /auth/me
- Include credentials (cookies) for all auth requests
- Send X-CSRF-Token from atlas_auth_csrf cookie for state-changing requests
- Remove or disable legacy local auth handlers and password logic
- Add/adjust route guards and UI guards based on returned rights
- Add integration tests for login bootstrap, auth failure, and rights enforcement
- Add migration notes and env var docs

Output:
1) files changed
2) endpoint mapping old -> new
3) tests added/updated
4) rollback plan via feature flag
```

## 14. Done definition

Migration is complete only when:

- DrawingExtractor has no active local credential verification path
- Auth context comes from AtlasUserAuth `/auth/me` only
- Rights enforcement is app-scoped with `appKey=drawing_extractor`
- Login/logout and cross-app session behavior verified in staging and production
