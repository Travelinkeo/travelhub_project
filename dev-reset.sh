#!/bin/bash
# ============================================================================
# dev-reset.sh
# ----------------------------------------------------------------------------
# Resetea el stack de desarrollo y lo deja funcional con datos sincronizados
# de produccion (solo schema, sin datos sensibles).
#
# Uso:
#   ./dev-reset.sh
#
# Prerequisitos:
#   - Stack de produccion corriendo (para clonar schema)
#   - .env con CLOUDFLARE_TUNNEL_TOKEN actualizado
#
# Que hace:
#   1. Para el stack de dev y borra volumenes (DB, redis, etc)
#   2. Levanta el stack de dev limpio
#   3. Espera a que los servicios esten healthy
#   4. Clona el schema de prod usando pg_dump --schema-only
#   5. Marca todas las migraciones como fake-applied
#   6. Crea superusuario admin/admin123 si no existe
#   7. Verifica que el dev web responda
# ============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.dev.yml"
PROJECT_NAME="travelhub-dev"
PROD_DB="TravelHub"
PROD_CONTAINER="travelhub_db"
PROD_USER="postgres"
PROD_DB_NAME="travelhub"
PROD_PASS="postgres"

ADMIN_USER="admin"
ADMIN_PASS="admin123"
ADMIN_EMAIL="admin@travelhub.local"

green() { printf "\033[32m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
blue() { printf "\033[34m%s\033[0m\n" "$*"; }

echo ""
blue "=== TravelHub - Reset Stack de Desarrollo ==="
echo ""

# 1. Verificar que prod este corriendo
if ! docker ps --format '{{.Names}}' | grep -q "^${PROD_CONTAINER}\$"; then
    red "ERROR: Container de produccion '${PROD_CONTAINER}' no esta corriendo."
    red "Necesito prod corriendo para clonar el schema."
    exit 1
fi
green "[OK] Container de produccion '${PROD_CONTAINER}' detectado"

# 2. Bajar dev stack y borrar volumenes
echo ""
blue "=== 1. Bajando dev stack y borrando volumenes ==="
cd "$PROJECT_DIR"
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" down -v 2>&1 | tail -3

# 3. Levantar dev stack
echo ""
blue "=== 2. Levantando dev stack limpio ==="
docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d 2>&1 | tail -5

# 4. Esperar a DB healthy
echo ""
blue "=== 3. Esperando a PostgreSQL (dev) ==="
for i in {1..30}; do
    if docker exec travelhub-dev-db-1 pg_isready -U postgres > /dev/null 2>&1; then
        green "  PostgreSQL listo (intento $i)"
        break
    fi
    sleep 2
done

# 5. Esperar a web
echo ""
blue "=== 4. Esperando a web (puede tardar 60s por system checks) ==="
for i in {1..60}; do
    S=$(docker inspect --format='{{.State.Status}}' travelhub-dev-web-1 2>/dev/null || echo "missing")
    if [ "$S" = "running" ]; then
        # Verificar puerto 8000
        if docker exec travelhub-dev-web-1 sh -c 'cat /proc/net/tcp6 | grep -i "1F40"' 2>/dev/null | head -1 | grep -q "1F40"; then
            green "  Web escuchando en puerto 8000 (intento $i)"
            break
        fi
    fi
    sleep 2
done

# 6. Clonar schema de prod
echo ""
blue "=== 5. Clonando schema de produccion ==="
docker exec "${PROD_CONTAINER}" pg_dump -U "${PROD_USER}" -d "${PROD_DB}" --schema-only --no-owner --no-acl > /tmp/prod_schema.sql
LINES=$(wc -l < /tmp/prod_schema.sql)
echo "  Schema exportado: $LINES lineas"

docker cp /tmp/prod_schema.sql travelhub-dev-db-1:/tmp/schema.sql
docker exec travelhub-dev-db-1 psql -U postgres -d travelhub -f /tmp/schema.sql 2>&1 | tail -3
docker exec travelhub-dev-db-1 rm /tmp/schema.sql
rm /tmp/prod_schema.sql

TABLES=$(docker exec travelhub-dev-db-1 psql -U postgres -d travelhub -tA -c "SELECT count(*) FROM pg_tables WHERE schemaname='public';")
green "  Tablas en dev DB: $TABLES"

# 7. Marcar migraciones como fake-applied
echo ""
blue "=== 6. Marcando migraciones como fake-applied ==="
docker exec travelhub-dev-web-1 python manage.py migrate --fake --noinput 2>&1 | tail -3

# 8. Crear superusuario admin
echo ""
blue "=== 7. Creando superusuario admin ==="
docker exec -i travelhub-dev-web-1 python manage.py shell << PYEOF
from django.contrib.auth import get_user_model
User = get_user_model()
u, created = User.objects.get_or_create(
    username='${ADMIN_USER}',
    defaults={'email': '${ADMIN_EMAIL}', 'is_staff': True, 'is_superuser': True}
)
u.email = '${ADMIN_EMAIL}'
u.is_staff = True
u.is_superuser = True
u.set_password('${ADMIN_PASS}')
u.save()
print(f"  User: created={created}, superuser={u.is_superuser}, staff={u.is_staff}")
PYEOF

# 9. Test final
echo ""
blue "=== 8. Verificando conectividad ==="
sleep 5
HTTP_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 30 http://localhost:8001/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ]; then
    green "  Dev web responde: HTTP $HTTP_CODE"
else
    red "  Dev web NO responde: HTTP $HTTP_CODE"
    red "  Revisa logs: docker logs travelhub-dev-web-1"
    exit 1
fi

CSS_CODE=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 http://localhost:8001/static/core/css/tailwind-built.css 2>/dev/null || echo "000")
if [ "$CSS_CODE" = "200" ]; then
    green "  CSS servido: HTTP $CSS_CODE"
else
    yellow "  CSS NO encontrado: HTTP $CSS_CODE (revisar despues)"
fi

echo ""
green "=== Stack de desarrollo listo! ==="
echo ""
echo "  Acceso dev:    http://localhost:8001"
echo "  Login:         ${ADMIN_USER} / ${ADMIN_PASS}"
echo "  Acceso prod:   https://travelhub.cc (sigue corriendo)"
echo ""
echo "  Comandos utiles:"
echo "    Ver logs:        docker logs -f travelhub-dev-web-1"
echo "    Shell dev web:   docker exec -it travelhub-dev-web-1 python manage.py shell"
echo "    Parar dev:       docker compose -p ${PROJECT_NAME} -f docker-compose.dev.yml down"
echo "    Bajar dev + DB:  docker compose -p ${PROJECT_NAME} -f docker-compose.dev.yml down -v"
echo ""
