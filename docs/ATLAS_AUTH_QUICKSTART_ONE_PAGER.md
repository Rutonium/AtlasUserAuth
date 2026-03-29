# AtlasUserAuth Quickstart One-Pager

Last updated: 2026-03-30
Audience: App teams planning migration to shared Atlas authentication

## Goal

Migrate an Atlas app from local auth to AtlasUserAuth with low risk and clear rollback.

## What Changes

- Login/logout/session move to AtlasUserAuth
- App keeps only app-specific authorization (`role` + `rights`)
- `appKey` identifies which app rights to return

## 60-Second Checklist

1. Define `ATLAS_AUTH_APP_KEY` for app.
2. Add env config (`ATLAS_AUTH_BASE_URL`, `USE_ATLAS_AUTH=true`, timeout).
3. Replace login call with `POST /api/auth/login` (cookies included).
4. Bootstrap user via `GET /api/auth/me?appKey=<app_key>`.
5. Replace logout with `POST /api/auth/logout` + CSRF header.
6. Guard app features using returned `rights` and `role`.
7. Remove local credential/session logic.
8. Run staging test matrix.
9. Roll out behind feature flag.

## Required Endpoints

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me?appKey=<app_key>`

## Required Request Rules

- Always include cookies (`credentials: include`)
- For state-changing requests, send:
  - `X-CSRF-Token` from `atlas_auth_csrf` cookie

## Minimum App Config

```env
ATLAS_AUTH_BASE_URL=https://atlas.subcpartner.com/atlas_user_auth
ATLAS_AUTH_APP_KEY=<your_app_key>
ATLAS_AUTH_TIMEOUT_SECONDS=10
USE_ATLAS_AUTH=true
```

## Definition of Done

- No active local credential verification path
- No local session ownership logic
- App rights come only from `/auth/me` for configured `appKey`
- Login, rights, and logout pass staging validation

## Rollback Plan

- Keep feature flag `USE_ATLAS_AUTH`
- Roll back by setting `USE_ATLAS_AUTH=false`
- Re-enable only after issue is fixed and retested

## Where to Read More

- Generic full guide: `docs/ATLAS_APP_AUTH_INTEGRATION_GUIDE.md`
- DrawingExtractor-specific guide: `docs/DRAWING_EXTRACTOR_AUTH_REWRITE_GUIDE.md`
