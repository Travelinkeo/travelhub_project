# Despliegue en Railway - TravelHub

**Fecha**: 25 de Enero de 2025  
**Plan**: Hobby ($5/mes)

---

## 📋 Pasos de Despliegue

### 1. Crear Proyecto en Railway

1. Ir a https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Seleccionar `Travelinkeo/travelhub_project`
4. Railway detectará Django automáticamente

### 2. Agregar PostgreSQL

1. En el proyecto, click "New"
2. "Database" → "Add PostgreSQL"
3. Railway crea automáticamente `DATABASE_URL`

### 3. Agregar Redis

1. Click "New" → "Database" → "Add Redis"
2. Railway crea automáticamente `REDIS_URL`

### 4. Configurar Variables de Entorno

En "Variables" del servicio Django, agregar:

```env
# Django
DEBUG=False
SECRET_KEY=<generar_nueva_clave_50_caracteres>
ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}}

# Database (automático)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (automático)
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

# Gmail
GMAIL_USER=boletotravelinkeo@gmail.com
GMAIL_APP_PASSWORD=lnacmrmbuxgouefg
EMAIL_HOST_USER=boletotravelinkeo@gmail.com
EMAIL_HOST_PASSWORD=lnacmrmbuxgouefg
DEFAULT_FROM_EMAIL=boletotravelinkeo@gmail.com

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=<tu_sid>
TWILIO_AUTH_TOKEN=<tu_token>
TWILIO_WHATSAPP_NUMBER=+14155238886

# Gemini
GEMINI_API_KEY=<tu_clave>

# Stripe (opcional)
STRIPE_SECRET_KEY=<tu_clave>
STRIPE_PUBLISHABLE_KEY=<tu_clave>
STRIPE_WEBHOOK_SECRET=<tu_clave>
```

### 5. Crear Servicios Worker y Beat

**Worker**:
1. Click "New" → "Empty Service"
2. Name: `travelhub-worker`
3. Settings → Start Command: `celery -A travelhub worker --loglevel=info`
4. Variables: Copiar TODAS las variables del servicio web

**Beat**:
1. Click "New" → "Empty Service"
2. Name: `travelhub-beat`
3. Settings → Start Command: `celery -A travelhub beat --loglevel=info`
4. Variables: Copiar TODAS las variables del servicio web

### 6. Deploy

Railway desplegará automáticamente los 3 servicios.

### 7. Ejecutar Comandos Iniciales

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link al proyecto
railway link

# Ejecutar migraciones
railway run python manage.py migrate

# Crear superusuario
railway run python manage.py createsuperuser

# Cargar catálogos
railway run python manage.py load_catalogs

# Crear agencia demo (opcional)
railway run python manage.py crear_agencia_demo
```

---

## ✅ Verificación

### Verificar Servicios

1. **Web**: Abrir URL pública de Railway
2. **Worker**: Ver logs - debe mostrar "celery@... ready"
3. **Beat**: Ver logs - debe mostrar "Scheduler: Sending due task..."

### Verificar Tareas Automáticas

Esperar 5 minutos y verificar logs de Worker:
```
[2025-01-25 10:05:00] Task core.monitor_boletos_email[...] received
[2025-01-25 10:05:05] Task core.monitor_boletos_email[...] succeeded
```

### Verificar Email

Enviar email de prueba a `boletotravelinkeo@gmail.com` y verificar que:
1. Se procese automáticamente (máximo 5 minutos)
2. Llegue email a `travelinkeo@gmail.com`
3. Llegue WhatsApp a `+584126080861`

---

## 🎯 URLs Importantes

- **Web**: `https://tu-proyecto.railway.app`
- **Admin**: `https://tu-proyecto.railway.app/admin/`
- **API**: `https://tu-proyecto.railway.app/api/`

---

## 💰 Costos Estimados

- **Plan Hobby**: $5/mes base
- **PostgreSQL**: Incluido
- **Redis**: Incluido
- **3 servicios**: Incluidos
- **Total**: ~$5-10/mes dependiendo del uso

---

## 🚨 Troubleshooting

### Worker no inicia

```bash
railway logs --service travelhub-worker
```

Verificar que `REDIS_URL` esté configurada.

### Beat no ejecuta tareas

```bash
railway logs --service travelhub-beat
```

Verificar que todas las variables estén copiadas del servicio web.

### Migraciones fallan

```bash
railway run python manage.py showmigrations
railway run python manage.py migrate --fake-initial
```

---

**Última actualización**: 25 de Enero de 2025  
**Estado**: Listo para desplegar  
**Autor**: Amazon Q Developer
