#!/bin/bash

echo "⏳ Esperando a que PostgreSQL inicie..."
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
python -c "
import socket, time
while True:
    try:
        s = socket.create_connection(('$POSTGRES_HOST', int('$POSTGRES_PORT')), timeout=2)
        s.close()
        break
    except OSError:
        time.sleep(1)
"
echo "✅ PostgreSQL iniciado."

# Fix permissions for appuser-writable directories
mkdir -p /app/media/boletos_importados /app/staticfiles
chown -R appuser:appgroup /app/media /app/staticfiles /app/boletos_importados 2>/dev/null || true

python manage.py migrate --noinput || echo "⚠️ Migrate falló (continuando)..."
python manage.py collectstatic --noinput &
echo "📦 collectstatic lanzado en background. Iniciando servidor..."

# Drop privileges to appuser for the main process
exec su appuser -c 'exec "$@"' appuser "$@"
