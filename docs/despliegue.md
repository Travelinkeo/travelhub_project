# Guía de Despliegue — TravelHub

**Entorno:** WSL2 (Ubuntu) + Docker Compose + Cloudflare Tunnel
**Propósito:** Esta guía explica cómo poner TravelHub en funcionamiento, tanto para desarrollo local como para producción.

> **Nota para personal no técnico:** TravelHub se ejecuta dentro de *contenedores* (como "cajas" aisladas que contienen cada servicio). No es necesario que entiendas todos los comandos, pero sí que sepas que existen estas instrucciones para cuando un técnico las necesite.

---

## Índice

1. [Requisitos previos](#1-requisitos-previos)
2. [Configuración inicial](#2-configuración-inicial)
3. [Variables de entorno](#3-variables-de-entorno)
4. [Levantar servicios](#4-levantar-servicios)
5. [Primer arranque](#5-primer-arranque)
6. [Despliegue en producción](#6-despliegue-en-producción)
7. [Compartir en red local](#7-compartir-en-red-local)
8. [Exponer con túneles (ngrok / Cloudflare)](#8-exponer-con-túneles)
9. [Mantenimiento](#9-mantenimiento)
10. [Resolución de problemas](#10-resolución-de-problemas)

---

## 1. Requisitos Previos

- Windows 10/11 con **WSL2** instalado (o Linux nativo)
- **Docker Desktop** (con integración WSL2) o Docker Engine
- **Git** para clonar el repositorio
- Cuenta en **Cloudflare** con un dominio configurado (solo producción)
- Opcional: **ngrok** para pruebas rápidas

---

## 2. Configuración Inicial

```bash
# Clonar el repositorio
git clone <repo-url> travelhub
cd travelhub

# Crear archivo de variables de entorno desde la plantilla
cp .env.example .env
```

Una vez creado `.env`, edítalo con tus valores reales (ver sección siguiente).

---

## 3. Variables de Entorno

Las variables de entorno son como las "configuraciones secretas" de la aplicación. Nunca deben compartirse ni subirse al repositorio.

### Variables críticas

| Variable | Descripción | ¿Para qué sirve? |
|----------|-------------|------------------|
| `SECRET_KEY` | Clave secreta de Django (mín. 50 caracteres) | Firma sesiones, tokens y datos sensibles |
| `ENCRYPTION_KEY` | Clave Fernet para datos cifrados | Protege campos sensibles en la base de datos |
| `DATABASE_URL` | URL de conexión a PostgreSQL | Dónde se almacenan todos los datos |
| `REDIS_URL` | URL de conexión a Redis | Caché, sesiones y colas de tareas |
| `GEMINI_API_KEY` | API Key de Google Gemini | Funcionalidades de inteligencia artificial |
| `STRIPE_SECRET_KEY` | Clave secreta de Stripe | Procesamiento de pagos |
| `STRIPE_PUBLISHABLE_KEY` | Clave pública de Stripe | Frontend de pagos |
| `RESEND_API_KEY` | API Key de Resend | Envío de correos electrónicos |
| `WPP_CONFIG_SECRET_KEY` | Token para WhatsApp | Mensajería WhatsApp |
| `GOTENBERG_URL` | URL del servicio Gotenberg | Generación de documentos PDF |
| `BINANCE_WEBHOOK_SECRET` | Secreto para Binance Pay | Pagos con criptomonedas |
| `SENTRY_DSN` | DSN de Sentry (opcional) | Monitoreo de errores |

### Entornos

- **Desarrollo:** usa `.env` con `DEBUG=True`
- **Producción:** usa `.env.production` con `DEBUG=False` y `ALLOWED_HOSTS` configurado

---

## 4. Levantar Servicios

### Desarrollo

```bash
docker-compose up --build -d
```

### Producción

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Servicios incluidos

| Servicio | Puerto | ¿Qué hace? |
|----------|--------|------------|
| `web` | 8000 | Aplicación Django (Gunicorn) |
| `db` | 5432 | Base de datos PostgreSQL |
| `redis` | 6379 | Caché y mensajería |
| `celery-worker` | - | Tareas en segundo plano (correos, IA, WhatsApp) |
| `celery-beat` | - | Tareas programadas (backups, recordatorios) |
| `nginx` | 80 | Archivos estáticos e imágenes |
| `traefik` | 443 | Proxy inverso con SSL (solo producción) |
| `gotenberg` | 3000 | Generación de PDF |
| `evolution` | 8080 | API de WhatsApp |

### Verificar estado

```bash
docker-compose ps
docker-compose logs -f web
```

---

## 5. Primer Arranque

La primera vez que levantas los servicios, debes preparar la base de datos:

```bash
# Ejecutar migraciones (crea las tablas en la BD)
docker-compose exec web python manage.py migrate

# Crear superusuario (administrador del sistema)
docker-compose exec web python manage.py createsuperuser

# Cargar datos iniciales
docker-compose exec web python manage.py seed_data            # Catálogos básicos
docker-compose exec web python manage.py seed_plan_contable  # Plan de cuentas contable
docker-compose exec web python manage.py setup_proveedores_vzla  # Proveedores Venezuela
```

### Verificación

```bash
# Health check (prueba de que el sistema responde)
curl http://localhost:8000/health/

# Acceder desde el navegador:
# - Admin:    http://localhost:8000/admin/
# - Dashboard: http://localhost:8000/dashboard/
# - API Docs:  http://localhost:8000/api/docs/
```

---

## 6. Despliegue en Producción

Para un entorno de producción seguro y escalable:

### 6.1 Preparar el servidor

- Servidor Ubuntu 22.04+ o similar
- Docker y Docker Compose instalados
- Dominio configurado con Cloudflare
- Puerto 443 abierto (HTTPS)

### 6.2 Configurar Cloudflare Tunnel

Cloudflare Tunnel expone el servidor a internet sin necesidad de abrir puertos en el firewall:

```bash
# Instalar cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Autenticar
cloudflared tunnel login

# Crear tunnel
cloudflared tunnel create travelhub

# Configurar en config.yml
# tunnel: travelhub
# credentials-file: /root/.cloudflared/<tunnel-id>.json
# ingress:
#   - hostname: tudominio.com
#     service: http://localhost:8000
#   - service: http_status:404

# Iniciar tunnel
cloudflared tunnel run travelhub
```

### 6.3 Pasos finales

```bash
# Construir y levantar
docker compose -f docker-compose.prod.yml up -d --build

# Migraciones
docker compose -f docker-compose.prod.yml exec web python manage.py migrate

# Archivos estáticos
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

# Crear superusuario
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Verificar seguridad
docker compose -f docker-compose.prod.yml exec web python manage.py check --deploy
```

---

## 7. Compartir en Red Local

Para probar TravelHub desde otros dispositivos en la misma red (ej. celular, tablet):

```bash
# Obtener la IP local
ip addr show | grep inet

# Acceder desde otro dispositivo en la misma red:
# http://<TU_IP_LOCAL>:8000
```

Asegúrate de que el puerto 8000 esté permitido en el firewall de Windows/Linux.

---

## 8. Exponer con Túneles

### ngrok (para pruebas rápidas)

```bash
# Descargar ngrok desde https://ngrok.com/download
# Descomprimir y ejecutar:
ngrok http 8000
```

ngrok genera una URL pública (`https://<random>.ngrok.io`) que redirige a tu `localhost:8000`.

### Cloudflare Tunnel (para producción)

Ver sección 6.2 arriba. Cloudflare es más seguro y estable que ngrok para uso continuo.

---

## 9. Mantenimiento

### Backups de base de datos

Los backups se ejecutan automáticamente a las 3:00 AM (retención: 7 días).

```bash
# Backup manual
docker-compose exec web python manage.py backup_database
# Los backups se guardan en: travelhub/backups/

# Backup manual con pg_dump
docker compose -f docker-compose.prod.yml exec db pg_dump -U postgres travelhub > backup_$(date +%Y%m%d).sql

# Restaurar backup
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres travelhub < backup_20260512.sql
```

### Logs (registros del sistema)

```bash
# Todos los servicios
docker-compose logs -f

# Solo errores de Django
docker-compose logs web | grep ERROR

# Servicios específicos en producción
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f celery
docker compose -f docker-compose.prod.yml logs -f celery-beat
```

### Actualizar el sistema

```bash
git pull
docker-compose up --build -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
```

---

## 10. Resolución de Problemas

### Error: "SECRET_KEY debe tener al menos 50 caracteres"

Genera una nueva clave:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Error: "WHATSAPP_MICROSERVICE_TOKEN no configurado"

Verifica que `WPP_CONFIG_SECRET_KEY` esté definido en `.env`.

### Error: "DATABASE_URL no definida"

Asegúrate de que `DATABASE_URL` esté correctamente configurada en `.env`.

### Celery no procesa tareas

1. Verificar conexión a Redis:
   ```bash
   redis-cli -h redis -p 6379 ping
   ```
2. Reiniciar workers:
   ```bash
   docker-compose restart celery-worker celery-beat
   ```

### TravelHub no arranca en el puerto 80

TravelHub está diseñado para ejecutarse en el puerto 8000 (directo) o detrás de Traefik (puerto 443 con SSL). No debe ejecutarse directamente en el puerto 80.

### La base de datos no responde

```bash
# Verificar que PostgreSQL está corriendo
docker-compose ps db

# Ver logs de la base de datos
docker-compose logs db
```
