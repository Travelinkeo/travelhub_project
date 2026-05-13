# Guía de Despliegue para Producción - TravelHub SaaS

Esta guía cubre el despliegue seguro y escalable de TravelHub en un entorno de producción.

## Requisitos Previos

- Servidor con Ubuntu 22.04+ o similar
- Docker y Docker Compose instalados
- Dominio configurado con Cloudflare
- Base de datos PostgreSQL 16+
- Redis 7+

## Variables de Entorno Obligatorias

Crea un archivo `.env.production` con:

```env
# Django
DEBUG=False
SECRET_KEY=<generar-con-django-get-random-secret-key>
ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com

# Base de Datos
DATABASE_URL=postgresql://user:password@db-host:5432/travelhub

# Redis
CELERY_BROKER_URL=redis://redis-host:6379/0
CELERY_RESULT_BACKEND=redis://redis-host:6379/0

# IA
GEMINI_API_KEY=tu-api-key

# Email (Resend o SendGrid)
RESEND_API_KEY=tu-api-key
# o
SENDGRID_API_KEY=tu-api-key

# WhatsApp
WHATSAPP_MICROSERVICE_URL=http://evolution-api:8080
WHATSAPP_MICROSERVICE_TOKEN=tu-token

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Seguridad
ENCRYPTION_KEY=<32-caracteres-minimo>
BINANCE_WEBHOOK_SECRET=tu-secret

# Frontend
FRONTEND_URL=https://tu-dominio.com
MAGIC_LINK_BASE_URL=https://tu-dominio.com
```

## Pasos de Despliegue

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-org/travelhub.git
cd travelhub
git checkout main
```

### 2. Configurar Variables de Entorno

```bash
cp .env.example .env.production
# Editar .env.production con valores reales
```

### 3. Construir y Levantar Contenedores

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### 4. Ejecutar Migraciones

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```

### 5. Recopilar Archivos Estáticos

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

### 6. Crear Superusuario

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### 7. Verificar Despliegue

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py check --deploy
```

## Configuración de Cloudflare Tunnel

1. Instalar `cloudflared` en el servidor
2. Autenticar con Cloudflare:
   ```bash
   cloudflared tunnel login
   ```
3. Crear tunnel:
   ```bash
   cloudflared tunnel create travelhub
   ```
4. Configurar routing en `config.yml`:
   ```yaml
   tunnel: travelhub
   credentials-file: /root/.cloudflared/<tunnel-id>.json
   ingress:
     - hostname: tu-dominio.com
       service: http://localhost:8000
     - service: http_status:404
   ```
5. Iniciar tunnel:
   ```bash
   cloudflared tunnel run travelhub
   ```

## Monitoreo

### Logs

```bash
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f celery
docker compose -f docker-compose.prod.yml logs -f celery-beat
```

### Health Checks

- API: `https://tu-dominio.com/api/health/`
- Admin: `https://tu-dominio.com/admin/`
- Swagger: `https://tu-dominio.com/api/docs/`

## Backup de Base de Datos

```bash
# Backup manual
docker compose -f docker-compose.prod.yml exec db pg_dump -U postgres travelhub > backup_$(date +%Y%m%d).sql

# Restaurar
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres travelhub < backup_20260512.sql
```

## Actualización

```bash
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## Troubleshooting

### Error: "SECRET_KEY debe tener al menos 50 caracteres"

Genera una nueva clave:
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Error: "WHATSAPP_MICROSERVICE_TOKEN no configurado"

Asegúrate de que `WHATSAPP_MICROSERVICE_TOKEN` esté definido en `.env.production`.

### Error: "DATABASE_URL no definida"

Verifica que `DATABASE_URL` esté correctamente configurada y accesible desde el servidor.

### Celery no procesa tareas

1. Verificar conexión a Redis:
   ```bash
   redis-cli -h redis-host ping
   ```
2. Reiniciar workers:
   ```bash
   docker compose -f docker-compose.prod.yml restart celery celery-beat
   ```

## Seguridad Adicional

- Configurar firewall (UFW) para permitir solo puertos 80, 443 y SSH
- Habilitar actualizaciones automáticas de seguridad
- Configurar fail2ban para protección contra fuerza bruta
- Monitorear logs con Sentry (configurado en `settings.py`)
