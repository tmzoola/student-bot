#!/bin/sh
set -e

echo "▶ Running database migrations..."
alembic upgrade head

echo "▶ Starting server..."
cd app
# --proxy-headers + --forwarded-allow-ips make uvicorn honor the reverse
# proxy's X-Forwarded-Proto/Host, so url_for() generates https URLs behind TLS.
WORKERS="${UVICORN_WORKERS:-2}"
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers "$WORKERS" \
    --proxy-headers --forwarded-allow-ips='*'
