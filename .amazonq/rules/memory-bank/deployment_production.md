# Deployment a Producción - TravelHub

**Fecha**: 21 de Enero de 2025  
**Objetivo**: Guía completa para desplegar TravelHub en producción

---

## 🚀 Opción Recomendada: Railway.app

### Por qué Railway

- ✅ **Gratis para empezar**: $5 USD crédito mensual
- ✅ **PostgreSQL + Redis incluidos**: Sin configuración adicional
- ✅ **Deploy automático**: Push a GitHub y despliega
- ✅ **SSL gratis**: HTTPS automático
- ✅ **Celery Beat**: Soporte nativo para workers

---

## 📋 Preparación del Proyecto

### 1. Archivos Necesarios

Ya creados:
- ✅ `Procfile` - Define web, worker, beat
- ✅ `railway.json` - Configuración de Railway
- ✅ `requirements.txt` - Dependencias Python
- ✅ `travelhub/celery_beat_schedule.py` - Tareas programadas

### 2. Variables de Entorno Requeridas

```env
# Django
DEBUG=False
SECRET_KEY=<generar_nueva_clave_50_caracteres>
ALLOWED_HOSTS=*.railway.app

# Database (Railway las genera automáticamente)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (Railway las genera automáticamente)
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

# Email
EMAIL_HOST_USER=<tu_email>
EMAIL_HOST_PASSWORD=<tu_password>
DEFAULT_FROM_EMAIL=<tu_email>

# Gemini API
GEMINI_API_KEY=<tu_clave>

# Stripe
STRIPE_SECRET_KEY=<sk_live_...>
STRIPE_PUBLISHABLE_KEY=<pk_live_...>
STRIPE_WEBHOOK_SECRET=<whsec_...>
STRIPE_PRICE_ID_BASIC=<price_...>
STRIPE_PRICE_ID_PRO=<price_...>
STRIPE_PRICE_ID_ENTERPRISE=<price_...>

# WhatsApp (opcional)
TWILIO_ACCOUNT_SID=<tu_sid>
TWILIO_AUTH_TOKEN=<tu_token>
TWILIO_WHATSAPP_NUMBER=<tu_numero>

# Frontend URL
FRONTEND_URL=https://tu-frontend.vercel.app
```

---

## 🔧 Deployment en Railway

### Paso 1: Crear Proyecto

1. Ir a https://railway.app
2. Login con GitHub
3. "New Project" → "Deploy from GitHub repo"
4. Seleccionar `travelhub_project`

### Paso 2: Agregar Servicios

```
+ Add Service → PostgreSQL
+ Add Service → Redis
```

Railway creará automáticamente:
- `DATABASE_URL`
- `REDIS_URL`

### Paso 3: Configurar Variables de Entorno

En el dashboard de Railway, agregar todas las variables listadas arriba.

### Paso 4: Configurar Servicios

Railway detectará automáticamente el `Procfile` y creará 3 servicios:

1. **Web** (Django)
   - Comando: `gunicorn travelhub.wsgi:application`
   - Puerto: Automático

2. **Worker** (Celery)
   - Comando: `celery -A travelhub worker`
   - Sin puerto público

3. **Beat** (Celery Beat)
   - Comando: `celery -A travelhub beat`
   - Sin puerto público

### Paso 5: Deploy

Railway desplegará automáticamente. Monitorea los logs.

### Paso 6: Ejecutar Comandos Iniciales

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Ejecutar migraciones
railway run python manage.py migrate

# Crear superusuario
railway run python manage.py createsuperuser

# Cargar catálogos
railway run python manage.py load_catalogs

# Crear agencia demo
railway run python manage.py crear_agencia_demo
```

---

## 📊 Tareas Programadas (Celery Beat)

### Configuración Automática

Las tareas se ejecutan automáticamente según `celery_beat_schedule.py`:

| Tarea | Frecuencia | Descripción |
|-------|------------|-------------|
| **Sincronizar BCV** | Diario 9:00 AM | Actualiza tasa de cambio |
| **Notificaciones Billing** | Diario 8:00 AM | Emails de trial, límites |
| **Recordatorios Pago** | Diario 10:00 AM | Recordatorios pendientes |
| **Cierre Mensual** | Día 1 2:00 AM | Cierre contable |
| **Monitor Tickets** | Cada 15 min | Monitorea emails |
| **Reset Ventas** | Día 1 0:00 AM | Resetea contador mensual |

### Reemplazo de Scripts .bat

| Script .bat (Windows) | Tarea Celery (Producción) |
|----------------------|---------------------------|
| `sincronizar_bcv.bat` | `sincronizar_tasa_bcv_task` |
| `enviar_recordatorios.bat` | `enviar_recordatorios_pago_task` |
| `cierre_mensual.bat` | `cierre_mensual_task` |
| Monitor manual | `monitor_tickets_email_task` |

---

## 🔍 Monitoreo

### Logs en Railway

```bash
# Ver logs del web server
railway logs --service web

# Ver logs del worker
railway logs --service worker

# Ver logs del beat
railway logs --service beat
```

### Verificar Tareas

```bash
# Ejecutar tarea manualmente
railway run python manage.py enviar_notificaciones_billing

# Ver estado de Celery
railway run celery -A travelhub inspect active
```

---

## 🆘 Troubleshooting

### Worker no inicia

**Problema**: Celery worker no se inicia  
**Solución**: Verificar que Redis esté conectado
```bash
railway logs --service worker
```

### Beat no ejecuta tareas

**Problema**: Tareas programadas no se ejecutan  
**Solución**: Verificar que el servicio beat esté corriendo
```bash
railway logs --service beat
```

### Migraciones fallan

**Problema**: Error al ejecutar migraciones  
**Solución**: Verificar DATABASE_URL
```bash
railway run python manage.py showmigrations
```

---

## 💰 Costos Estimados

### Railway.app

| Usuarios/Mes | Web | Worker | Beat | PostgreSQL | Redis | Total |
|--------------|-----|--------|------|------------|-------|-------|
| 0-100 | $0 | $0 | $0 | $0 | $0 | **$0** |
| 100-500 | $5 | $5 | $5 | $0 | $0 | **$15/mes** |
| 500-2000 | $10 | $10 | $5 | $5 | $5 | **$35/mes** |

### Render.com (Alternativa)

| Usuarios/Mes | Web | Worker | PostgreSQL | Redis | Total |
|--------------|-----|--------|------------|-------|-------|
| 0-100 | $0 | $0 | $0 | $0 | **$0** |
| 100-500 | $7 | $7 | $0 | $0 | **$14/mes** |
| 500-2000 | $25 | $25 | $7 | $10 | **$67/mes** |

---

## 🔐 Seguridad en Producción

### Checklist

- [ ] `DEBUG=False` en producción
- [ ] `SECRET_KEY` único y seguro (50+ caracteres)
- [ ] `ALLOWED_HOSTS` configurado correctamente
- [ ] HTTPS habilitado (automático en Railway)
- [ ] Variables de entorno seguras (no en código)
- [ ] Stripe en modo LIVE (no test)
- [ ] Webhook de Stripe con URL de producción
- [ ] Backups de base de datos configurados

---

## 📚 Recursos

- **Railway Docs**: https://docs.railway.app
- **Celery Docs**: https://docs.celeryproject.org
- **Django Deployment**: https://docs.djangoproject.com/en/5.0/howto/deployment/

---

**Última actualización**: 21 de Enero de 2025  
**Estado**: Guía completa para producción  
**Autor**: Amazon Q Developer
