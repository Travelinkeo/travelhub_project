#!/bin/bash
# ============================================================================
# Test de migración limpia (fresh migrate)
# ============================================================================
# Crea una BD temporal vacía y corre `manage.py migrate` desde cero para
# detectar si el historial de migrations puede reconstruir un schema válido.
#
# Esto es el test que documenta el problema de la triple representación de
# `Moneda` (ver docs/MIGRATIONS.md). Si este test pasa, fresh migrate funciona.
#
# Uso:
#   bash scripts/diagnostics/test_fresh_migrate.sh
#
# Requisitos:
#   - El stack de dev (docker compose) corriendo, con servicio `db` y `web`.
#   - Variables POSTGRES_USER/POSTGRES_PASSWORD en el entorno o por defecto
#     postgres/postgres.
#
# No toca la BD de desarrollo principal.
# ============================================================================
set -euo pipefail

PROJECT_NAME="${COMPOSE_PROJECT:-travelhub-dev}"
TEST_DB="travelhub_freshtest"
PGUSER="${POSTGRES_USER:-postgres}"

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*"; }
blue()  { printf "\033[34m%s\033[0m\n" "$*"; }

blue "=== Test fresh DB migrate (project: $PROJECT_NAME) ==="

# 1. Recrear la BD de test
echo "[1/4] Recreando DB '$TEST_DB'..."
docker compose -p "$PROJECT_NAME" exec -T db psql -U "$PGUSER" -d postgres \
  -c "DROP DATABASE IF EXISTS $TEST_DB;" > /dev/null
docker compose -p "$PROJECT_NAME" exec -T db psql -U "$PGUSER" -d postgres \
  -c "CREATE DATABASE $TEST_DB;" > /dev/null

# 2. Limpiar __pycache__ de migrations para forzar recarga
echo "[2/4] Limpiando __pycache__..."
docker compose -p "$PROJECT_NAME" exec -T web \
  find /app -path "*/migrations/__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

# 3. Correr migrate contra la BD temporal
echo "[3/4] Corriendo migrate contra $TEST_DB (puede tardar 1-2 min)..."
EXIT_CODE=0
docker compose -p "$PROJECT_NAME" exec -T \
  -e DATABASE_URL="postgresql://$PGUSER:$PGUSER@db:5432/$TEST_DB" \
  -e SENTRY_DSN="" \
  web python manage.py migrate --noinput --verbosity 2 \
  > /tmp/migrate_output.txt 2>&1 || EXIT_CODE=$?

# 4. Resultado
echo "[4/4] Resultado: exit=$EXIT_CODE"

if [ "$EXIT_CODE" -eq 0 ]; then
  green ""
  green "=== MIGRATE EXITOSO ==="
  TABLES=$(docker compose -p "$PROJECT_NAME" exec -T db psql -U "$PGUSER" -d "$TEST_DB" \
    -tA -c "SELECT count(*) FROM pg_tables WHERE schemaname='public';" 2>/dev/null || echo "?")
  MIGS=$(docker compose -p "$PROJECT_NAME" exec -T db psql -U "$PGUSER" -d "$TEST_DB" \
    -tA -c "SELECT count(*) FROM django_migrations;" 2>/dev/null || echo "?")
  green "Tablas creadas: $TABLES"
  green "Migraciones aplicadas: $MIGS"
else
  red ""
  red "=== MIGRATE FALLÓ ==="
  red ""
  red "== Últimas 60 líneas del error =="
  tail -60 /tmp/migrate_output.txt
  red ""
  red "== Errores relevantes =="
  grep -iE "django.db.utils|ProgrammingError|relation.*does not exist|relation.*already exists|column.*does not exist|column.*already exists" \
    /tmp/migrate_output.txt | head -20 || true
fi

# Limpieza: borrar la BD temporal
echo ""
echo "Limpiando DB temporal '$TEST_DB'..."
docker compose -p "$PROJECT_NAME" exec -T db psql -U "$PGUSER" -d postgres \
  -c "DROP DATABASE IF EXISTS $TEST_DB;" > /dev/null

exit "$EXIT_CODE"
