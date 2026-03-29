# Real Stack Connection and Test (SQL + Employee API)

Use this to connect AtlasUserAuth to real SQL Server and employee API, then validate end-to-end.

## 1. Configure `backend/.env.local`

Start from:

```bash
cp backend/.env.example backend/.env.local
```

Set at minimum:

```env
ATLAS_AUTH_DB_URL=mssql+pyodbc://<user>:<pass>@<server>/<db>?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes
EMPLOYEE_API_BASE_URL=http://common.subcpartner.com
EMPLOYEE_API_TOKEN=<real_token>
EMPLOYEE_API_AUTH_HEADER=Authorization
EMPLOYEE_API_AUTH_SCHEME=

SESSION_SIGNING_SECRET=<long_random_secret>
LOCAL_ADMIN_PASSWORD=<break_glass_password>
ATLAS_AUTH_PORT=5020
```

## 2. Run preflight checks (DB + employee API)

```bash
./backend/scripts/test_real_stack.sh backend/.env.local
```

This verifies:

- SQL connectivity (`SELECT 1`)
- `dbo.AtlasUsers` is reachable
- employee API auth and payload shape
- local health endpoint if app is running

## 3. Start app on real config

```bash
cd backend
./scripts/run_local.sh
```

`run_local.sh` always loads `backend/.env.local`.

## 4. Validate auth flow with curl

In another terminal:

```bash
rm -f /tmp/atlas_cookie.txt

# Login (example uses break-glass local admin)
curl -i -c /tmp/atlas_cookie.txt \
  -H 'Content-Type: application/json' \
  -d '{"employee_id":"0","password":"<LOCAL_ADMIN_PASSWORD>"}' \
  http://127.0.0.1:5020/api/auth/login

# Current user context for app key
curl -b /tmp/atlas_cookie.txt \
  "http://127.0.0.1:5020/api/auth/me?appKey=drawing_extractor"

# Admin list users
curl -b /tmp/atlas_cookie.txt \
  "http://127.0.0.1:5020/api/auth/users"

# Logout (CSRF header required)
CSRF=$(awk '$6=="atlas_auth_csrf" {print $7}' /tmp/atlas_cookie.txt)
curl -i -b /tmp/atlas_cookie.txt \
  -H "X-CSRF-Token: ${CSRF}" \
  -X POST \
  "http://127.0.0.1:5020/api/auth/logout"
```

## 5. Validate via UI

- Open `http://127.0.0.1:5020/`
- Login
- Open `/admin`
- Try provisioning by EmployeeID and rights update

## 6. Common blockers

- ODBC driver missing: install `ODBC Driver 18 for SQL Server` and unixODBC packages
- DB auth/network issue: verify SQL reachability and credentials
- employee API 401/403: verify token/header/scheme
- CSRF 403 on logout/admin: include `X-CSRF-Token` from `atlas_auth_csrf` cookie
