#!/bin/bash
# ============================================================================
# SCRIPT DE EMERGENCIA - TravelHub Production
# ============================================================================
# Este script resuelve el error: relation "axes_accessattempt" does not exist
# Ejecutar en el servidor de producción via SSH
# ============================================================================

set -e

echo "=========================================="
echo "  SCRIPT DE EMERGENCIA - TRAVELHUB"
echo "=========================================="
echo ""
echo "Este script ejecutará todas las migraciones pendientes"
echo "para resolver el error de axes_accessattempt."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: No se encontró docker-compose.yml"
    echo "   Ejecutar este script desde el directorio del proyecto"
    exit 1
fi

# Paso 1: Verificar que los contenedores estén corriendo
echo "📊 Verificando estado de contenedores..."
docker-compose ps

echo ""
echo "🗄️  Ejecutando migraciones de base de datos..."
echo "=========================================="

# Paso 2: Ejecutar todas las migraciones pendientes
docker-compose exec web python manage.py migrate --noinput

echo ""
echo "✅ Migraciones completadas exitosamente"
echo ""

# Paso 3: Verificar que las tablas de axes existan
echo "🔍 Verificando tablas de axes..."
docker-compose exec web python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'axes_%'\")
tables = [row[0] for row in cursor.fetchall()]
if tables:
    print(f'✅ Tablas de axes encontradas: {tables}')
else:
    print('❌ No se encontraron tablas de axes')
    exit(1)
"

echo ""
echo "=========================================="
echo "  ¡REPARACIÓN COMPLETADA!"
echo "=========================================="
echo ""
echo "El login debería funcionar correctamente ahora."
echo "Por favor, intenta hacer login en https://travelhub.cc/login/"
echo ""
