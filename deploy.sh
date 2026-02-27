#!/bin/bash

# Script de Despliegue Automatizado para TravelHub
# Uso: ./deploy.sh

set -e

echo "🚀 Iniciando despliegue de TravelHub..."

# 1. Verificar existencia de .env
if [ ! -f .env ]; then
    echo "❌ Error: Archivo .env no encontrado. Por favor, créalo basándote en .env.example"
    exit 1
fi

# 2. Actualizar código (opcional si se corre dentro del repo)
# git pull origin main

# 3. Levantar la infraestructura
echo "📦 Construyendo y levantando contenedores..."
docker-compose up --build -d

# 4. Limpiar imágenes huérfanas
echo "🧹 Limpiando imágenes antiguas..."
docker image prune -f

echo "📊 Estado de los servicios:"
docker-compose ps

echo "✅ Despliegue completado con éxito."
echo "🌐 El sitio debería estar disponible en el puerto 80 (vía Nginx)."
