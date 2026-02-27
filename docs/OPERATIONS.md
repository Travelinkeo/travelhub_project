# Manual de Operaciones TravelHub

**Versión:** 1.0
**Última Actualización:** 28 de Noviembre de 2025

Guía para el despliegue, monitoreo y mantenimiento del sistema en producción.

## 1. Arquitectura de Despliegue
El sistema está diseñado para correr containerizado (Docker) en un VPS gestionado por **Coolify**.

### Servicios Requeridos
1.  **Web:** Contenedor Django (Gunicorn).
2.  **Worker:** Contenedor Celery (para parser de emails).
3.  **Beat:** Contenedor Celery Beat (tareas programadas).
4.  **DB:** PostgreSQL 15+.
5.  **Cache/Broker:** Redis 7+.

## 2. Despliegue con Coolify

### Preparación del Repositorio
Asegurarse de que existan en la raíz:
*   `Dockerfile` (Optimizado para Python 3.13).
*   `docker-compose.yml` (Opcional, Coolify puede autodetectar).
*   `nixpacks.toml` (Si se usa Nixpacks).

### Variables de Entorno (Producción)
Configurar en el panel de Coolify:
```ini
DEBUG=False
ALLOWED_HOSTS=app.travelhub.com
DATABASE_URL=...
REDIS_URL=...
# Seguridad
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

## 3. Mantenimiento y Monitoreo

### Logs
*   **Web:** Ver logs de Gunicorn para errores 500.
*   **Celery:** Revisar logs del Worker si los boletos no se procesan automáticamente.

### Backups
*   **Base de Datos:** Configurar backup diario automático en Coolify (S3 o Local).
*   **Media:** La carpeta `media/` (donde se guardan los PDFs de boletos) debe estar en un volumen persistente o usar almacenamiento externo (AWS S3 / Cloudinary).

### Resolución de Problemas Comunes

#### El Parser falló al leer un boleto
1.  Revisar el log en `BoletoImportado` (Admin).
2.  Verificar si la aerolínea cambió el formato del PDF.
3.  Si es un formato nuevo, actualizar `core/ticket_parser.py` y desplegar.

#### Error de "TemplateSyntaxError"
Si ocurre en producción, verificar que `dashboard.html` no esté corrupto. En caso de emergencia, usar el script `fix_dashboard.py` vía SSH.
