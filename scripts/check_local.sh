#!/usr/bin/env sh
set -eu
# Manual checks only — intentionally no GitHub Actions.
cd "$(dirname "$0")/.."
python3 -m compileall -q backend
: "${DATABASE_URL:?Set DATABASE_URL to disposable PostgreSQL testing database}"
: "${DJANGO_SECRET_KEY:?Set DJANGO_SECRET_KEY}"
: "${DJANGO_ALLOWED_HOSTS:?Set DJANGO_ALLOWED_HOSTS}"
: "${REDIS_URL:?Set REDIS_URL}"
(cd backend && python3 manage.py check && python3 manage.py makemigrations --check --dry-run && python3 manage.py migrate --noinput && python3 manage.py test)
# Lockfile will be generated during initial development; pin and audit before production.
(cd frontend && npm install --no-audit --no-fund && npm run build)
echo "All local gates passed; manual UX/security review is still needed."
