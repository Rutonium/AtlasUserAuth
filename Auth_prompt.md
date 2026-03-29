# Atlas Shared Authentication - Build Prompt

You are a world class software developer specialising in cybersecurity and user authentication but has a love for simple solutions.

Design and implement a standalone **Atlas Auth** service that provides shared login/session for multiple Atlas applications, while keeping rights/roles independent per app.

## Project Context

I currently have multiple Atlas apps (including DrawingExtractor) each with duplicated login/admin logic. I want one shared auth service to remove duplication.

### Known Environment and Preferences

- Primary stack preference: **Python** backend (FastAPI style)
- UI/layout preference: **Atlas style** (clean, practical, simple)
- Database: **SQL Server** via `mssql+pyodbc`
- OS/runtime: **Debian Linux**
- Reverse proxy: **nginx**
- Process manager: **systemd**
- Existing deploy pattern: app services deployed under `/home/rune/dev/...`
- Existing shared host/IP pattern uses nginx path-based routing (for example `/drawing_extractor/`)
- Existing auth data source is `dbo.AtlasUsers`

## Goal

Create a standalone auth service (not embedded in DrawingExtractor) that gives:

1. One login experience for all Atlas apps
2. Login memory across apps in the same browser session
3. Per-app independent role/rights control
4. Strong but practical security defaults
5. Easy onboarding of new apps

## Architecture Requirements

### 1) Service Boundaries

Build a separate service named `atlas_auth` with its own:

- codebase
- runtime
- deployment unit
- nginx route

It must not depend on DrawingExtractor uptime/releases.

### 2) Identity and Access Model

Use existing identity table:

- `dbo.AtlasUsers`

Credential fields are centralized here (password/PIN hash+salt etc.).

Create (or specify migration for) a dedicated app-access table:

- `dbo.AtlasAppAccess`

Recommended columns:

- `EmployeeID` (FK-like reference to AtlasUsers)
- `AppKey` (e.g. `drawing_extractor`, `asset_management`, `people_planner`)
- `Role` (string)
- `RightsJson` (JSON object)
- `IsActive` (bit)
- `CreatedAt`, `UpdatedAt`
- Unique index on (`EmployeeID`, `AppKey`)

### 3) Shared Session / SSO Behavior

Implement session behavior so users log in once and are remembered across Atlas apps in same browser session.

Preferred approach:

- secure server-side session + signed HttpOnly cookie
- same parent Atlas domain and cookie scope compatible with all Atlas apps
- short idle timeout + absolute max lifetime

Support optional token mode (Bearer JWT) only if truly needed, but keep primary implementation simple.

### 4) Per-App Authorization

Each app sends `appKey` (server-trusted config, not user-editable) when resolving current user context.

Auth service returns user profile + role + rights for that app only.

Do not mix app permissions.

### 5) Employee Directory Integration (For New User Provisioning)

When creating/provisioning users, the flow must start from **EmployeeID** and validate against the existing employee directory API.

Use this upstream API contract:

- Method/URL: `GET {EMPLOYEE_API_BASE_URL}/Employees/all`
- Auth header name: `EMPLOYEE_API_AUTH_HEADER` (default `Authorization`)
- Auth token: `EMPLOYEE_API_TOKEN`
- Optional auth scheme prefix: `EMPLOYEE_API_AUTH_SCHEME` (if set, send `"{scheme} {token}"`, otherwise send token raw)
- Timeout: 20 seconds

Expected upstream payload shape (array of employees):

- `number` (employee number)
- `name`
- `initials`
- `eMail`
- `departmentCode`

Normalization rules:

- `number` is the source for EmployeeID
- Employee number must be numeric for current Atlas system
- Normalize to canonical numeric string/integer form (e.g. `"00123"` -> `123`)
- Ignore malformed rows without valid numeric `number` or missing `name`

Reliability requirements:

- Cache employee list for 300 seconds to keep login/provisioning fast
- If refresh fails and cache exists, keep serving cached entries
- Expose directory cache status and last error in a diagnostics endpoint

Provisioning requirement:

- Admin can create/provision app access by entering EmployeeID
- Service must first resolve EmployeeID from directory data, then create/update Atlas auth records
- Do not allow provisioning of unknown EmployeeID values not present in directory

## API Requirements

Design and implement at least:

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me?appKey={appKey}`
- `GET /auth/users` (admin)
- `PUT /auth/users/{employeeId}/apps/{appKey}` (admin rights/role update)
- `POST /auth/users/{employeeId}/reset-credential` (admin)
- `POST /auth/users/provision-by-employee-id` (admin; validates employee from directory first)
- `GET /auth/employees/search?q=...` (admin helper for employee lookup from cached directory)

For login UX compatibility, support employee-based login and optional local break-glass admin account from env.

## Security Requirements (Must Have)

- PBKDF2-HMAC-SHA256 verification (or stronger approved KDF if proposed)
- Generic auth failure responses (no account enumeration)
- Rate limit + lockout per IP and per account
- CSRF protection for cookie-authenticated state-changing endpoints
- Secure cookie flags: `HttpOnly`, `Secure`, `SameSite` (with clear environment handling)
- Input validation via Pydantic schemas
- Structured auth audit logging (login success/fail, lockout, admin changes)
- No secrets hardcoded; env-only configuration
- Principle of least privilege for DB account

## Operational Requirements (Debian + systemd + nginx)

Provide:

1. `requirements.txt`
2. `.env.example`
3. SQL migration scripts for required schema changes
4. systemd unit file (e.g. `atlas_auth.service`)
5. nginx config snippet for path or subdomain routing
6. deployment notes tailored to Debian
7. health endpoints:
   - `/healthz`
   - `/api/healthz` (including DB status)

Keep conventions similar to my existing deployment style.

## Coding Style Requirements

- Prefer simple, maintainable implementation over over-engineered abstractions.
- Clear module layout in Atlas style, for example:
  - `app/main.py`
  - `app/core/settings.py`
  - `app/db/session.py`
  - `app/services/auth_service.py`
  - `app/services/session_service.py`
  - `app/schemas/*.py`
- Keep code comments concise and only where needed.
- Include practical error handling with useful server logs.

## Deliverables Required From You

Produce a full implementation proposal with:

1. Final architecture summary
2. DB schema/migration SQL
3. Endpoint contracts (request/response examples)
4. Backend code skeleton or full code (FastAPI)
5. Security controls mapping
6. Deploy artifacts (systemd/nginx/env)
7. Integration steps for DrawingExtractor as first client app
8. Rollout plan for remaining Atlas apps

## DrawingExtractor Integration Requirement

Show exactly how DrawingExtractor should switch from local auth endpoints to Atlas Auth:

- login flow changes
- cookie/session handling
- replacing current `/api/auth/*` behavior
- keeping app-specific rights checks via `appKey=drawing_extractor`

## Output Format

Respond in this order:

1. High-level design (short)
2. SQL migration(s)
3. Backend implementation
4. Security hardening checklist
5. Deployment steps (Debian/systemd/nginx)
6. DrawingExtractor migration steps
7. Risks and fallback plan

Keep solutions practical, secure, and as simple as possible.
