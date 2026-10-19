# Production-like staging (NOT a production approval)
Build: docker compose -f compose.yaml -f compose.production.yaml build.
Start only on controlled staging: docker compose -f compose.yaml -f compose.production.yaml up -d.
The frontend listens only on 127.0.0.1:8080, backend on 127.0.0.1:8000.
An external **trusted TLS proxy** is mandatory for the public domain; sanitize X-Forwarded-Proto there and set DJANGO_ALLOWED_HOSTS, CSRF trusted origins, production DB/Redis secrets and secure cookies.
The frontend Dockerfile deliberately requires package-lock.json and npm ci, missing lockfile blocks the build. No dev Vite server should be exposed.
Do NOT run these commands on a live instance holding customer records without backups, rollback instructions, tested migrations and approval.
The overlay has not been deployed/tested from this environment. Before release: run scripts/commercial_acceptance.sh on disposable staging, browser E2E and external audit.
