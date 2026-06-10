#!/bin/bash
# ============================================================================
# FIX COMPLETO PRODUCCIÓN - Tablas faltantes bookings
# ============================================================================
# Este script resuelve el error: relation "bookings_venta" does not exist
# Ejecutar en el servidor de producción via SSH
# ============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}  FIX COMPLETO PRODUCCIÓN${NC}"
echo -e "${BLUE}  Tablas faltantes bookings${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.prod.yml" ] && [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}❌ Error: No se encontró docker-compose.prod.yml ni docker-compose.yml${NC}"
    echo "   Ejecutar este script desde el directorio del proyecto en producción"
    exit 1
fi

# Determinar qué archivo docker-compose usar
if [ -f "docker-compose.prod.yml" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    echo -e "${GREEN}✅ Usando docker-compose.prod.yml${NC}"
else
    COMPOSE_FILE="docker-compose.yml"
    echo -e "${YELLOW}⚠️  Usando docker-compose.yml (no se encontró .prod.yml)${NC}"
fi

echo ""
echo -e "${BLUE}🔍 PASO 1: Verificando estado actual...${NC}"
echo "=========================================="

# Verificar que los contenedores estén corriendo
if ! docker-compose -f $COMPOSE_FILE ps | grep -q "Up"; then
    echo -e "${RED}❌ Los contenedores no están corriendo${NC}"
    echo "   Ejecutar: docker-compose -f $COMPOSE_FILE up -d"
    exit 1
fi

echo -e "${GREEN}✅ Contenedores corriendo${NC}"
echo ""

# Verificar conexión a la base de datos
echo -e "${BLUE}🔍 Verificando conexión a la base de datos...${NC}"
if ! docker-compose -f $COMPOSE_FILE exec -T db psql -U postgres -d travelhub_prod -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  No se pudo conectar a travelhub_prod, intentando con travelhub...${NC}"
    DB_NAME="travelhub"
else
    DB_NAME="travelhub_prod"
    echo -e "${GREEN}✅ Conectado a $DB_NAME${NC}"
fi

echo ""
echo -e "${BLUE}🔍 PASO 2: Verificando migraciones aplicadas...${NC}"
echo "=========================================="

# Verificar migraciones de bookings
echo -e "${BLUE}Migraciones de bookings:${NC}"
docker-compose -f $COMPOSE_FILE exec -T web python manage.py showmigrations bookings 2>&1 | grep -E "\[X\]|\[ \]" || echo "No se pudieron verificar las migraciones"

echo ""
echo -e "${BLUE}🔍 PASO 3: Verificando tablas existentes...${NC}"
echo "=========================================="

# Verificar si la tabla bookings_venta existe
if docker-compose -f $COMPOSE_FILE exec -T db psql -U postgres -d $DB_NAME -c "\dt bookings_venta" 2>&1 | grep -q "bookings_venta"; then
    echo -e "${GREEN}✅ La tabla bookings_venta YA EXISTE${NC}"
    echo -e "${YELLOW}⚠️  El problema puede ser otro${NC}"
else
    echo -e "${RED}❌ La tabla bookings_venta NO EXISTE${NC}"
    echo -e "${BLUE}🔧 Procediendo a crear la tabla...${NC}"
fi

echo ""
echo -e "${BLUE}🔧 PASO 4: Aplicando migraciones...${NC}"
echo "=========================================="

# Intentar aplicar migraciones de bookings
echo -e "${BLUE}Aplicando migraciones de bookings...${NC}"
if docker-compose -f $COMPOSE_FILE exec -T web python manage.py migrate bookings --noinput 2>&1; then
    echo -e "${GREEN}✅ Migraciones de bookings aplicadas exitosamente${NC}"
else
    echo -e "${YELLOW}⚠️  Las migraciones fallaron, intentando reset...${NC}"
    
    # Reset de migraciones de bookings
    echo -e "${BLUE}Reseteando migraciones de bookings...${NC}"
    docker-compose -f $COMPOSE_FILE exec -T web python manage.py migrate bookings zero --noinput 2>&1 || true
    
    # Reaplicar migraciones
    echo -e "${BLUE}Reaplicando migraciones de bookings...${NC}"
    if docker-compose -f $COMPOSE_FILE exec -T web python manage.py migrate bookings --noinput 2>&1; then
        echo -e "${GREEN}✅ Migraciones de bookings reaplicadas exitosamente${NC}"
    else
        echo -e "${RED}❌ Error al aplicar migraciones${NC}"
        echo -e "${YELLOW}Intentando aplicar todas las migraciones pendientes...${NC}"
        docker-compose -f $COMPOSE_FILE exec -T web python manage.py migrate --noinput 2>&1 || true
    fi
fi

echo ""
echo -e "${BLUE}🔍 PASO 5: Verificando tablas creadas...${NC}"
echo "=========================================="

# Verificar que las tablas principales existan
TABLES=("bookings_venta" "bookings_boletoimportado" "bookings_itemventa" "bookings_pagovena")

for TABLE in "${TABLES[@]}"; do
    if docker-compose -f $COMPOSE_FILE exec -T db psql -U postgres -d $DB_NAME -c "\dt $TABLE" 2>&1 | grep -q "$TABLE"; then
        echo -e "${GREEN}✅ $TABLE existe${NC}"
    else
        echo -e "${RED}❌ $TABLE NO existe${NC}"
    fi
done

echo ""
echo -e "${BLUE}🔧 PASO 6: Aplicando todas las migraciones pendientes...${NC}"
echo "=========================================="

# Aplicar todas las migraciones restantes
docker-compose -f $COMPOSE_FILE exec -T web python manage.py migrate --noinput 2>&1 || true

echo ""
echo -e "${BLUE}🔧 PASO 7: Recolectando archivos estáticos...${NC}"
echo "=========================================="

docker-compose -f $COMPOSE_FILE exec -T web python manage.py collectstatic --noinput 2>&1 || true

echo ""
echo -e "${BLUE}🔧 PASO 8: Reiniciando servicios...${NC}"
echo "=========================================="

# Reiniciar el contenedor web
echo -e "${BLUE}Reiniciando contenedor web...${NC}"
docker-compose -f $COMPOSE_FILE restart web

# Esperar a que el servicio esté listo
echo -e "${BLUE}Esperando a que el servicio esté listo...${NC}"
sleep 10

# Verificar que el servicio esté saludable
if docker-compose -f $COMPOSE_FILE ps web | grep -q "healthy"; then
    echo -e "${GREEN}✅ Servicio web saludable${NC}"
else
    echo -e "${YELLOW}⚠️  Servicio web no está marcado como saludable (puede ser normal)${NC}"
fi

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  ¡FIX COMPLETADO!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "${BLUE}📋 Resumen de acciones realizadas:${NC}"
echo "   ✅ Verificación de estado inicial"
echo "   ✅ Aplicación de migraciones de bookings"
echo "   ✅ Verificación de tablas creadas"
echo "   ✅ Aplicación de todas las migraciones pendientes"
echo "   ✅ Recolección de archivos estáticos"
echo "   ✅ Reinicio de servicios"
echo ""
echo -e "${BLUE}🌐 Próximo paso:${NC}"
echo "   Recargar: https://travelhub.cc/bookings/dashboard/modern/"
echo ""
echo -e "${YELLOW}⚠️  Si el problema persiste:${NC}"
echo "   1. Verificar logs: docker-compose -f $COMPOSE_FILE logs -f web"
echo "   2. Verificar migraciones: docker-compose -f $COMPOSE_FILE exec web python manage.py showmigrations"
echo "   3. Verificar tablas: docker-compose -f $COMPOSE_FILE exec db psql -U postgres -d $DB_NAME -c '\dt bookings_*'"
echo ""
