#!/bin/bash
# ============================================================================
# VERIFICACIÓN POST-FIX - Producción
# ============================================================================
# Este script verifica que el fix se aplicó correctamente
# Ejecutar después de fix_completo_produccion.sh
# ============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  VERIFICACIÓN POST-FIX${NC}"
echo -e "${BLUE}  Producción${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Determinar qué archivo docker-compose usar
if [ -f "docker-compose.prod.yml" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

# Determinar nombre de la base de datos
if docker-compose -f $COMPOSE_FILE exec -T db psql -U postgres -d travelhub_prod -c "SELECT 1" > /dev/null 2>&1; then
    DB_NAME="travelhub_prod"
else
    DB_NAME="travelhub"
fi

echo -e "${BLUE}🔍 Verificación 1: Estado de contenedores${NC}"
echo "=========================================="
docker-compose -f $COMPOSE_FILE ps
echo ""

echo -e "${BLUE}🔍 Verificación 2: Tablas de bookings${NC}"
echo "=========================================="
docker-compose -f $COMPOSE_FILE exec -T db psql -U postgres -d $DB_NAME -c "\dt bookings_*"
echo ""

echo -e "${BLUE}🔍 Verificación 3: Conteo de registros en bookings_venta${NC}"
echo "=========================================="
docker-compose -f $COMPOSE_FILE exec -T db psql -U postgres -d $DB_NAME -c "SELECT COUNT(*) as total_ventas FROM bookings_venta;"
echo ""

echo -e "${BLUE}🔍 Verificación 4: Migraciones aplicadas${NC}"
echo "=========================================="
docker-compose -f $COMPOSE_FILE exec -T web python manage.py showmigrations bookings 2>&1 | grep -E "\[X\]" | wc -l
echo "migraciones de bookings aplicadas"
echo ""

echo -e "${BLUE}🔍 Verificación 5: Health check del servicio web${NC}"
echo "=========================================="
if docker-compose -f $COMPOSE_FILE exec -T web python -c "import urllib.request; response = urllib.request.urlopen('http://localhost:8000/health/'); print(response.read().decode())" 2>&1; then
    echo -e "${GREEN}✅ Servicio web respondiendo correctamente${NC}"
else
    echo -e "${RED}❌ Servicio web no responde${NC}"
fi
echo ""

echo -e "${BLUE}🔍 Verificación 6: Logs recientes del servicio web${NC}"
echo "=========================================="
docker-compose -f $COMPOSE_FILE logs --tail=20 web
echo ""

echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  VERIFICACIÓN COMPLETADA${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${BLUE}📋 Si todas las verificaciones pasaron:${NC}"
echo "   ✅ El fix se aplicó correctamente"
echo "   ✅ El dashboard debería funcionar"
echo ""
echo -e "${BLUE}🌐 Prueba final:${NC}"
echo "   Abrir: https://travelhub.cc/bookings/dashboard/modern/"
echo ""
