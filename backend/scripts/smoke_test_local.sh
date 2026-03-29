#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:5020}"

echo "Smoke test against: $BASE_URL"

curl -fsS "$BASE_URL/" >/dev/null
curl -fsS "$BASE_URL/login" >/dev/null
curl -fsS "$BASE_URL/Login" >/dev/null
curl -fsS "$BASE_URL/admin" >/dev/null
curl -fsS "$BASE_URL/healthz" >/dev/null
curl -fsS "$BASE_URL/api/healthz" >/dev/null

echo "Core smoke checks passed: login aliases + pages + health endpoints."

echo "Optional auth smoke skipped by default (requires SQL Server schema + data)."
