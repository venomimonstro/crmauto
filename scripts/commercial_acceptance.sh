#!/usr/bin/env bash
# Manual commercial readiness gate. Run ONLY against disposable staging.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [[ "${CONFIRM_DISPOSABLE_STAGING:-}" != "YES" ]]; then
  echo "ERROR: Set CONFIRM_DISPOSABLE_STAGING=YES on an isolated staging environment." >&2
  exit 4
fi
: "${DATABASE_URL:?PostgreSQL staging DSN is required}"
: "${DJANGO_SECRET_KEY:?Staging secret required}"
: "${DJANGO_ALLOWED_HOSTS:?Staging allowed hosts required}"
: "${REDIS_URL:?Staging Redis required}"
if [[ "${BILLING_ENFORCE_WRITES:-0}" != "1" ]]; then
  echo "BLOCKER: BILLING_ENFORCE_WRITES must be enabled." >&2
  exit 5
fi
if [[ ! -f frontend/package-lock.json ]]; then
  echo "BLOCKER: reproducible frontend/package-lock.json is required for npm ci." >&2
  exit 6
fi
python3 -m compileall -q backend
(
  cd backend
  python3 manage.py check --deploy --fail-level ERROR
  python3 manage.py makemigrations --check --dry-run
  # Database is explicitly disposable staging; validate actual schema evolution.
  python3 manage.py migrate --noinput
  # Discover every test module, including operational regression tests added later.
  python3 manage.py test --noinput --verbosity 2
)
(
  cd frontend
  npm ci --no-audit --no-fund
  npm run build
)
(
  cd backend
  python3 manage.py release_preflight
)
echo "Static/unit/build gates passed. Browser E2E, PSP/KKM, restore and pentest are still manual release requirements."
