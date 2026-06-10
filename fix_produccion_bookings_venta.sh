#!/bin/bash
# ============================================================================
# FIX PRODUCCIÓN - Tabla bookings_venta faltante
# ============================================================================
# Ejecutar en el servidor de producción via SSH
# ============================================================================

set -e

echo "=========================================="
echo "  FIX PRODUCCIÓN - bookings_venta"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: No se encontró docker-compose.prod.yml"
    echo "   Ejecutar este script desde el directorio del proyecto en producción"
    exit 1
fi

echo "🔍 Verificando estado actual..."
echo ""

# Paso 1: Verificar qué migraciones están marcadas como aplicadas
echo "📋 Migraciones de bookings aplicadas:"
docker-compose -f docker-compose.prod.yml exec web python manage.py showmigrations bookings 2>&1 | grep -E "\[X\]|\[ \]"

echo ""
echo "🔧 Aplicando migraciones reales (no fake)..."
echo "=========================================="

# Paso 2: Aplicar migraciones de bookings correctamente
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate bookings --noinput

echo ""
echo "✅ Migraciones de bookings aplicadas"
echo ""

# Paso 3: Verificar que la tabla existe
echo "🔍 Verificando tabla bookings_venta..."
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -d travelhub_prod -c "\dt bookings_venta"

echo ""
echo "=========================================="
echo "  ¡FIX COMPLETADO!"
echo "=========================================="
echo ""
echo "El dashboard debería funcionar correctamente ahora."
echo "Por favor, recarga https://travelhub.cc/bookings/dashboard/modern/"
echo ""
