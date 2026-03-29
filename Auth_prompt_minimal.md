# Atlas Auth Prompt (Minimal)

You are a world class software developer specialising in cybersecurity and user authentication but has a love for simple solutions.

Build a standalone `atlas_auth` service for shared login across Atlas apps.

## Must Achieve

- One login for multiple Atlas apps
- Login remembered across apps in same browser session
- Per-app independent rights/roles
- Simple, secure, maintainable implementation

## Environment / Preferences

- Python backend (FastAPI style)
- Debian Linux
- SQL Server via `mssql+pyodbc`
- nginx + systemd deployment
- Atlas-style practical layout
- Existing identity table: `dbo.AtlasUsers`

## Data Model

Keep credentials in `dbo.AtlasUsers`.

Add app-access table `dbo.AtlasAppAccess` with:

- `EmployeeID`
- `AppKey`
- `Role`
- `RightsJson`
- `IsActive`
- `CreatedAt`, `UpdatedAt`
- unique (`EmployeeID`, `AppKey`)

## Employee Directory (Provisioning Source)

When creating new users, provisioning must start from EmployeeID validated against employee API data.

Use:

- `GET {EMPLOYEE_API_BASE_URL}/Employees/all`
- Header name from `EMPLOYEE_API_AUTH_HEADER` (default `Authorization`)
- Token from `EMPLOYEE_API_TOKEN`
- Optional scheme from `EMPLOYEE_API_AUTH_SCHEME`
- Timeout 20s

Payload fields to consume:

- `number`, `name`, `initials`, `eMail`, `departmentCode`

Rules:

- `number` is EmployeeID source and must be numeric
- Normalize employee number to canonical numeric value
- Cache employee directory for 300s
- If refresh fails and cache exists, serve cache
- Do not provision unknown EmployeeID values

## API (minimum)

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me?appKey={appKey}`
- `GET /auth/users` (admin)
- `PUT /auth/users/{employeeId}/apps/{appKey}` (admin)
- `POST /auth/users/provision-by-employee-id` (admin; validates against directory)
- `GET /auth/employees/search?q=...` (admin helper lookup)

## Security Requirements

- PBKDF2-HMAC-SHA256 verification
- Generic invalid credential responses
- Rate limiting + lockout (IP and account)
- Secure HttpOnly cookie session across Atlas apps
- CSRF protection for state-changing routes
- Pydantic validation
- Structured auth audit logs
- Secrets from env only

## Deliverables

Provide in this order:

1. Architecture summary
2. SQL migration(s)
3. FastAPI implementation (files/modules)
4. systemd unit + nginx config snippet
5. `.env.example`
6. DrawingExtractor integration steps (`appKey=drawing_extractor`)
7. Rollout plan for other Atlas apps

Keep it practical and as simple as possible.
