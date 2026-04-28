#!/bin/bash
# Evitar que el script continúe si hay un error
set -e

echo "⏳ Esperando a que PostgreSQL inicie..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 1
done
echo "✅ PostgreSQL iniciado."

# Si el usuario pasó un comando (ej: python manage.py ...), lo ejecutamos y salimos
if [ $# -gt 0 ]; then
    echo "⚡ Ejecutando comando personalizado: $@"
    exec "$@"
fi

echo "📦 OMITIENDO migraciones de base de datos para depuración..."
# python manage.py migrate --noinput

echo "🎨 Recopilando archivos estáticos (Tailwind/CSS/JS)..."
# python manage.py collectstatic --noinput

echo "🚀 Iniciando Gunicorn (Servidor de Producción)..."
# Ejecuta Gunicorn con 4 workers (ajusta según los núcleos de tu VPS)
exec gunicorn travelhub.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 300 --graceful-timeout 120 --keep-alive 5
