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
chmod -R 755 /app/media /app/boletos_importados 2>/dev/null || true

echo "🚀 Iniciando servidor..."

# Drop privileges to appuser and execute container command
exec runuser -u appuser -- "$@"
