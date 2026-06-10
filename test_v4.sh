#!/bin/bash
cd /mnt/c/Users/ARMANDO/travelhub_project
docker compose -p travelhub-dev exec -T db psql -U postgres -c "DROP DATABASE IF EXISTS travelhub_freshtest;" > /dev/null
docker compose -p travelhub-dev exec -T db psql -U postgres -c "CREATE DATABASE travelhub_freshtest;" > /dev/null
docker compose -p travelhub-dev exec -T -e DATABASE_URL='postgresql://postgres:postgres@db:5432/travelhub_freshtest' web python manage.py migrate --noinput --verbosity 3 > /tmp/migrate.log 2>&1
echo "Exit: $?"
tail -80 /tmp/migrate.log
