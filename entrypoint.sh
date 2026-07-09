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

python manage.py migrate --noinput || echo "⚠️ Migrate falló (continuando)..."
python manage.py collectstatic --noinput &
echo "📦 collectstatic lanzado en background. Iniciando servidor..."

exec "$@"
