#!/bin/bash
# test_fresh_migrate.sh
# Crea una DB limpia en el postgres de dev y corre `migrate` desde cero.
# No toca la DB principal del dev stack.

set -e

cd /mnt/c/Users/ARMANDO/travelhub_project

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*"; }
blue() { printf "\033[34m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }

TEST_DB="travelhub_freshtest"

blue "=== Test fresh DB migrate ==="
echo

# 0. Verificar que dev-db este corriendo
if ! docker ps --format '{{.Names}}' | grep -q "travelhub-dev-db-1"; then
  red "ERROR: travelhub-dev-db-1 no esta corriendo"
  exit 1
fi

# 1. Recrear la DB de test
echo "[1/4] Recreando DB '$TEST_DB'..."
docker exec travelhub-dev-db-1 psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS $TEST_DB;" 2>&1 | tail -1
docker exec travelhub-dev-db-1 psql -U postgres -d postgres -c "CREATE DATABASE $TEST_DB;" 2>&1 | tail -1

# 2. Limpiar __pycache__ de migrations para forzar recarga
echo "[2/4] Limpiando __pycache__..."
find /mnt/c/Users/ARMANDO/travelhub_project -path "*/migrations/__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 3. Correr migrate con override de DATABASE_URL
echo "[3/4] Corriendo migrate contra $TEST_DB..."
echo "      (esto puede tomar 1-2 minutos)"
echo

docker exec \
  -e DATABASE_URL="postgresql://postgres:postgres@db:5432/${TEST_DB}" \
  -e DEBUG="True" \
  travelhub-dev-web-1 \
  python manage.py migrate --noinput 2>&1 | tee /tmp/migrate_output.txt | tail -30

EXIT_CODE=${PIPESTATUS[0]}
echo
echo "[4/4] Resultado: exit=$EXIT_CODE"

# Save the full log
cp /tmp/migrate_output.txt /mnt/c/Users/ARMANDO/travelhub_project/last_migrate_test.log

if [ "$EXIT_CODE" -eq 0 ]; then
  green ""
  green "=== MIGRATE EXITOSO ==="
  TABLES=$(docker exec travelhub-dev-db-1 psql -U postgres -d $TEST_DB -tA -c "SELECT count(*) FROM pg_tables WHERE schemaname='public';" 2>/dev/null)
  green "Tablas creadas: $TABLES"
  MIGS=$(docker exec travelhub-dev-db-1 psql -U postgres -d $TEST_DB -tA -c "SELECT count(*) FROM django_migrations;" 2>/dev/null)
  green "Migraciones aplicadas: $MIGS"
else
  red ""
  red "=== MIGRATE FALLO ==="
  red ""
  red "== ULTIMAS 60 LINEAS DEL ERROR =="
  tail -60 /tmp/migrate_output.txt
  red ""
  red "== BUSCANDO ERRORES ESPECIFICOS =="
  grep -iE "django.db.utils|ProgrammingError|relation.*does not exist|relation.*already exists|column.*does not exist|column.*already exists" /tmp/migrate_output.txt | head -20
  red ""
  red "Log completo: last_migrate_test.log"
fi
