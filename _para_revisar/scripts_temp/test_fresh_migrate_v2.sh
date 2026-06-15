#!/bin/bash
# Run fresh migrate test
set -e
cd /mnt/c/Users/ARMANDO/travelhub_project

# 1. Drop and create test DB on the dev postgres (PG 15)
echo "[1/4] Recreando DB 'travelhub_freshtest'..."
docker exec travelhub_db psql -U postgres -c "DROP DATABASE IF EXISTS travelhub_freshtest;" > /dev/null
docker exec travelhub_db psql -U postgres -c "CREATE DATABASE travelhub_freshtest;" > /dev/null

# 2. Clean pycache
echo "[2/4] Limpiando __pycache__..."
docker exec travelhub_web find /app -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

# 3. Run migrate
echo "[3/4] Corriendo migrate contra travelhub_freshtest..."
docker exec -e DATABASE_URL='postgresql://postgres:postgres@db:5432/travelhub_freshtest' \
  -e SENTRY_DSN="" \
  travelhub_web python manage.py migrate --noinput --verbosity 3 2>&1
