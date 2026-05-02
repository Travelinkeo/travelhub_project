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

# python manage.py migrate --noinput
# python manage.py collectstatic --noinput

# Ejecuta Gunicorn con auto-reload para desarrollo
exec gunicorn travelhub.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 300
