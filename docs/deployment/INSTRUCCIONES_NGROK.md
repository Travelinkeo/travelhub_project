# Instrucciones para Exponer TravelHub con Cloudflare Tunnel

## Paso 1: Iniciar los Servicios

```bash
# En WSL2, dentro del directorio del proyecto
docker-compose up -d
```

## Paso 2: Iniciar el Túnel Cloudflare

```bash
# En WSL2
cloudflared tunnel --url http://localhost:8000
```

Verás algo como:

```
Connecting to trycloudflare.com...
Your quick Tunnel has been created!
Visit it at: https://abc123.trycloudflare.com
```

Esa URL expone tu instancia local de TravelHub (puerto 8000) a internet.

## Paso 3: Acceder

1. **Dashboard principal:** `https://abc123.trycloudflare.com/dashboard/`
2. **Admin de Django:** `https://abc123.trycloudflare.com/admin/`
3. **Health check:** `https://abc123.trycloudflare.com/health/`

## Notas

- El túnel se corta al cerrar la terminal. Para túnel permanente, configura un túnel con nombre en Cloudflare Zero Trust.
- Asegúrate de que `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` en tu `.env` incluyan el dominio de Cloudflare.
