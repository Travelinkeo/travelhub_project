# Guía de Despliegue — TravelHub

**Setup:** WSL2 (Ubuntu) + Docker Compose + Cloudflare Tunnel

## Requisitos Previos

- Windows 10/11 con WSL2 instalado
- Docker Desktop (con integración WSL2)
- Cuenta de Cloudflare con un dominio configurado
- `cloudflared` instalado en WSL2

## 1. Configuración Inicial

```bash
# Clonar el repo dentro de WSL2
git clone <repo-url> travelhub
cd travelhub

# Crear .env desde el template
cp .env.example .env
# Editar .env con tus valores reales:
#   SECRET_KEY, ENCRYPTION_KEY, DATABASE_URL, GEMINI_API_KEY, STRIPE_SECRET_KEY, etc.
```

### Variables de Entorno Críticas

| Variable | Descripción |
|----------|-------------|
| `SECRET_KEY` | Clave Django (mínimo 50 caracteres) |
| `ENCRYPTION_KEY` | Clave Fernet para campos encriptados |
| `DATABASE_URL` | URL de PostgreSQL (postgres://...) |
| `REDIS_URL` | URL de Redis (redis://redis:6379/0) |
| `GEMINI_API_KEY` | API Key de Google Gemini |
| `STRIPE_SECRET_KEY` | Clave secreta de Stripe |
| `WPP_CONFIG_SECRET_KEY` | Token para microservicio WhatsApp |
| `GOTENBERG_URL` | URL del servicio Gotenberg (opcional) |

## 2. Levantar Servicios

```bash
# Construir e iniciar todos los servicios
docker-compose up --build -d

# Verificar estado
docker-compose ps

# Ver logs
docker-compose logs -f web
```

### Servicios

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `web` | 8000 | Django + Gunicorn |
| `db` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis 7 |
| `celery-worker` | - | Tareas asíncronas |
| `celery-beat` | - | Tareas programadas |

## 3. Túnel Cloudflare

```bash
# Instalar cloudflared en WSL2
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Iniciar túnel (reemplaza con tu dominio)
cloudflared tunnel --url http://localhost:8000
```

Esto expone `localhost:8000` a internet vía `https://<random>.trycloudflare.com` o tu dominio configurado.

## 4. Primer Arranque

```bash
# Ejecutar migraciones
docker-compose exec web python manage.py migrate

# Crear superusuario
docker-compose exec web python manage.py create_superuser_cli

# Cargar datos iniciales (catálogos, plan contable, proveedores)
docker-compose exec web python manage.py seed_data
docker-compose exec web python manage.py seed_plan_contable
docker-compose exec web python manage.py setup_proveedores_vzla
```

## 5. Verificación

```bash
# Health check
curl http://localhost:8000/health/

# Acceder al admin
# http://localhost:8000/admin/

# Acceder al dashboard
# http://localhost:8000/dashboard/
```

## 6. Mantenimiento

### Backups de Base de Datos

Los backups se ejecutan automáticamente a las 3:00 AM vía Celery Beat (7 días de retención).

```bash
# Backup manual
docker-compose exec web python manage.py backup_database

# Los backups se guardan en: travelhub/backups/
```

### Logs

```bash
# Todos los servicios
docker-compose logs -f

# Solo errores de Django
docker-compose logs web | grep ERROR
```

### Actualizar

```bash
git pull
docker-compose up --build -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py collectstatic --noinput
```
