#!/bin/bash

# Salir inmediatamente si un comando falla
set -e

# Función para esperar a que un servicio esté listo
wait_for_service() {
  local host="$1"
  local port="$2"
  local name="$3"
  
  echo "⏳ Esperando a que $name ($host:$port) esté listo..."
  while ! nc -z "$host" "$port"; do
    sleep 1
  done
  echo "✅ $name está listo!"
}

# 1. Esperar a la Base de Datos (Postgres)
if [ -n "$DB_HOST" ]; then
  wait_for_service "$DB_HOST" "${DB_PORT:-5432}" "PostgreSQL"
fi

# 2. Esperar a Redis
if [ -n "$REDIS_HOST" ]; then
    wait_for_service "$REDIS_HOST" "${REDIS_PORT:-6379}" "Redis"
fi

# 3. Solo el servicio 'web' debe correr migraciones y collectstatic
# Usamos una variable de entorno opcional para identificar el rol
if [ "$SERVICE_ROLE" = "web" ]; then
    echo "🚀 Ejecutando tareas de mantenimiento (Web)..."
    
    echo "📊 Aplicando migraciones..."
    python manage.py migrate --noinput
    
    echo "📂 Recopilando archivos estáticos..."
    python manage.py collectstatic --noinput
fi

# Ejecutar el comando pasado al contenedor
echo "🎬 Iniciando comando: $@"
exec "$@"
