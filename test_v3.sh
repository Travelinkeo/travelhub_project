#!/bin/bash
cd /mnt/c/Users/ARMANDO/travelhub_project
docker exec travelhub-dev-web-1 bash -c "find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; find /app -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; true"
docker compose -p travelhub-dev exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS travelhub_freshtest;" > /dev/null
docker compose -p travelhub-dev exec -T db psql -U postgres -c "CREATE DATABASE travelhub_freshtest;" > /dev/null
docker compose -p travelhub-dev exec -T -e DATABASE_URL='postgresql://postgres:postgres@db:5432/travelhub_freshtest' web python manage.py migrate --noinput --verbosity 3 2>&1 | tail -60
