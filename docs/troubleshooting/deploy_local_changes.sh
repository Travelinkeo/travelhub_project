#!/bin/bash
# deploy_local_changes.sh
# Copia los archivos modificados del host al contenedor travelhub_web
#
# ADVERTENCIAS:
# 1. Este proyecto NO tiene volume-bind al directorio del código fuente.
#    Cuando modificas archivos en tu máquina host, hay que copiarlos
#    manualmente al contenedor con este script.
#
# 2. Después de copiar, hay que limpiar __pycache__ y enviar SIGHUP a gunicorn
#    (que está corriendo con --preload). Sin esto, gunicorn sirve la versión
#    vieja del código en memoria.
#
# 3. Para cambios en models.py, urls_system.py, o migraciones → usar rebuild:
#       docker compose build web && docker compose up -d web
#
# Uso:
#   bash docs/troubleshooting/deploy_local_changes.sh

set -e

CONTAINER="travelhub_web"
WEB_ROOT="/app"

echo "[deploy_local_changes] Copiando archivos al contenedor $CONTAINER..."

# Lista de archivos modificados frecuentemente durante troubleshooting.
# Edita esta lista si modificas otros archivos.
FILES=(
    "core/views/evolution_qr_view.py"
    "core/views/agencia_views.py"
    "core/views/evolution_proxy_views.py"
    "core/urls_system.py"
    "apps/bookings/bookings_views.py"
    "apps/communications/services/evolution_api_service.py"
    "apps/common/tasks.py"
    "travelhub/celery_beat_schedule.py"
    "core/middleware.py"
    "core/templates/dashboard/partials/whatsapp_qr_new.html"
)

for file in "${FILES[@]}"; do
    src="$(pwd)/$file"
    dst="$WEB_ROOT/$file"

    if [ ! -f "$src" ]; then
        echo "  ⚠️  SKIP: $file (no existe en host)"
        continue
    fi

    docker cp "$src" "$CONTAINER:$dst"
    echo "  ✅ $file"
done

# Limpiar Bytecode caches
docker exec $CONTAINER sh -c "find $WEB_ROOT -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; find $WEB_ROOT -name '*.pyc' -delete 2>/dev/null" || true
echo "  ✅ __pycache__ limpiado"

echo ""
echo "[deploy_local_changes] Enviando SIGHUP al master de gunicorn..."

# Encontrar el PID master de gunicorn
MASTER_PID=$(docker exec $CONTAINER sh -c "
  for p in \$(ls /proc 2>/dev/null | grep -E '^[0-9]+\$'); do
    cmd=\$(tr '\\0' ' ' < /proc/\$p/cmdline 2>/dev/null | head -c 80)
    if echo \"\$cmd\" | grep -q 'gunicorn.*travelhub.wsgi'; then
      echo \$p
      break
    fi
  done
" 2>/dev/null)

if [ -n "$MASTER_PID" ]; then
    docker exec $CONTAINER sh -c "kill -HUP $MASTER_PID" 2>/dev/null || true
    echo "  ✅ SIGHUP enviado a PID $MASTER_PID"
else
    echo "  ⚠️  Master PID no encontrado, reiniciando contenedor..."
    docker restart $CONTAINER
fi

echo ""
echo "[deploy_local_changes] ✅ Deploy completo"
echo "  Espera 8-15 segundos para que gunicorn recargue los workers"
echo "  Verifica con: curl -s http://localhost:8000/system/whatsapp/health/"
