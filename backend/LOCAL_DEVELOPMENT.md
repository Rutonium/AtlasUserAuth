# AtlasUserAuth Local Development

## Prerequisites

- Python 3.11+
- `curl`

## Start locally

From repository root:

```bash
./backend/scripts/run_local.sh
```

The script will:

1. Create `backend/.venv` if missing
2. Install `backend/requirements.txt`
3. Create `backend/.env.local` with safe dev defaults (first run only)
4. Start `uvicorn` on `http://127.0.0.1:5020`

## Smoke test locally

In a second terminal:

```bash
./backend/scripts/smoke_test_local.sh
```

Checks:

- `/`
- `/admin`
- `/healthz`
- `/api/healthz`

## Notes about local DB mode

Default local mode uses sqlite (`ATLAS_AUTH_DB_URL=sqlite+pysqlite:///./local_dev.db`) to allow quick startup.

This mode is for boot/smoke checks only.

For full authentication and admin flow validation, run against SQL Server with real Atlas schema/data by setting:

- `ATLAS_AUTH_DB_URL`
- `EMPLOYEE_API_*`
- `SESSION_SIGNING_SECRET`
- `LOCAL_ADMIN_PASSWORD`

in `backend/.env.local`.
