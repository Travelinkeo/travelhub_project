# Troubleshooting: Celery en la Nube

**Fecha**: 25 de Enero de 2025  
**Problema**: Automatización de parseo de boletos no funciona en la nube

---

## 🔍 Diagnóstico Rápido

### 1. Verificar que los 3 servicios estén corriendo

En Render/Railway dashboard, verificar:
- ✅ **Web** (Django) - Estado: Running
- ✅ **Worker** (Celery) - Estado: Running
- ✅ **Beat** (Programador) - Estado: Running

**Si Beat no está corriendo**: Ese es el problema principal.

---

## 🛠️ Soluciones por Problema

### Problema 1: Beat no está corriendo

**Síntoma**: Worker funciona pero las tareas no se ejecutan automáticamente.

**Solución**:

1. Verificar que `render.yaml` tenga el servicio beat:
```yaml
- type: worker
  name: travelhub-beat
  env: python
  startCommand: celery -A travelhub beat --loglevel=info
```

2. En Render dashboard, verificar que el servicio "travelhub-beat" exista y esté "Running".

3. Si no existe, agregarlo manualmente:
   - New → Background Worker
   - Start Command: `celery -A travelhub beat --loglevel=info`

---

### Problema 2: Variables de entorno faltantes

**Síntoma**: Worker corre pero falla al procesar correos.

**Solución**: Verificar que TODAS estas variables estén configuradas en los 3 servicios:

```env
# Gmail
GMAIL_USER=boletotravelinkeo@gmail.com
GMAIL_APP_PASSWORD=lnacmrmbuxgouefg
EMAIL_HOST_USER=boletotravelinkeo@gmail.com
EMAIL_HOST_PASSWORD=lnacmrmbuxgouefg
DEFAULT_FROM_EMAIL=boletotravelinkeo@gmail.com

# Redis (automático en Render)
REDIS_URL=${REDIS_URL}

# Database (automático en Render)
DATABASE_URL=${DATABASE_URL}

# Twilio (opcional para WhatsApp)
TWILIO_ACCOUNT_SID=<tu_sid>
TWILIO_AUTH_TOKEN=<tu_token>
TWILIO_WHATSAPP_NUMBER=+14155238886
```

**Cómo agregar en Render**:
1. Ir a servicio → Environment
2. Add Environment Variable
3. Agregar cada variable
4. Redeploy

---

### Problema 3: Redis no conectado

**Síntoma**: Error "Connection refused" en logs de Worker/Beat.

**Solución**:

1. Verificar que Redis esté creado en Render:
   - Dashboard → Redis → travelhub-redis

2. Verificar que la variable `REDIS_URL` esté configurada:
   ```yaml
   envVars:
     - key: REDIS_URL
       fromService:
         name: travelhub-redis
         type: redis
         property: connectionString
   ```

3. Si no existe, crear Redis:
   - New → Redis
   - Name: travelhub-redis
   - Plan: Starter (gratis)

---

### Problema 4: Tareas no registradas

**Síntoma**: Beat corre pero no ejecuta las tareas.

**Solución**: Ejecutar script de diagnóstico:

```bash
# En shell de Render
python diagnostico_celery.py
```

Verificar que aparezcan:
```
4. TAREAS REGISTRADAS:
   - core.monitor_boletos_email
   - core.monitor_boletos_whatsapp
```

Si no aparecen, verificar que `core/tasks/__init__.py` importe las tareas:

```python
from .email_monitor_tasks import monitor_boletos_email, monitor_boletos_whatsapp
```

---

## 🧪 Tests Manuales

### Test 1: Ejecutar tarea manualmente

```bash
# En shell de Render o local
python test_celery_cloud.py
```

Debe mostrar:
```
✅ Resultado: {'success': True, 'procesados': X}
```

### Test 2: Verificar conexión Redis

```bash
python manage.py shell
>>> from redis import Redis
>>> from django.conf import settings
>>> r = Redis.from_url(settings.CELERY_BROKER_URL)
>>> r.ping()
True
```

### Test 3: Verificar Gmail

```bash
python manage.py shell
>>> from core.services.email_monitor_service import EmailMonitorService
>>> monitor = EmailMonitorService('email', 'test@test.com')
>>> # Si no da error, Gmail está configurado correctamente
```

---

## 📊 Ver Logs en Tiempo Real

### Render

```bash
# Logs de Beat
render logs --service travelhub-beat --tail

# Logs de Worker
render logs --service travelhub-worker --tail

# Logs de Web
render logs --service travelhub-web --tail
```

### Railway

```bash
# Logs de Beat
railway logs --service beat

# Logs de Worker
railway logs --service worker
```

---

## ✅ Checklist de Verificación

### Configuración
- [ ] 3 servicios corriendo (Web, Worker, Beat)
- [ ] Redis creado y conectado
- [ ] Variables de entorno configuradas en los 3 servicios
- [ ] `render.yaml` tiene los 3 servicios definidos

### Tareas
- [ ] Tareas registradas en Celery
- [ ] Schedule configurado en `celery_beat_schedule.py`
- [ ] Imports correctos en `core/tasks/__init__.py`

### Credenciales
- [ ] `GMAIL_USER` configurado
- [ ] `GMAIL_APP_PASSWORD` configurado
- [ ] `EMAIL_HOST_USER` configurado
- [ ] `REDIS_URL` configurado

### Tests
- [ ] `python diagnostico_celery.py` pasa
- [ ] `python test_celery_cloud.py` ejecuta sin errores
- [ ] Logs de Beat muestran "Scheduler: Sending due task..."

---

## 🚨 Errores Comunes

### Error: "No module named 'core.tasks'"

**Solución**: Crear `core/tasks/__init__.py`:
```python
from .email_monitor_tasks import monitor_boletos_email, monitor_boletos_whatsapp

__all__ = ['monitor_boletos_email', 'monitor_boletos_whatsapp']
```

### Error: "Connection refused" (Redis)

**Solución**: Verificar que `REDIS_URL` esté configurada y Redis esté corriendo.

### Error: "Authentication failed" (Gmail)

**Solución**: Verificar que `GMAIL_APP_PASSWORD` sea el App Password de Gmail, no la contraseña normal.

### Error: "Task not registered"

**Solución**: Verificar que el nombre de la tarea en `celery_beat_schedule.py` coincida con el `@shared_task(name='...')`.

---

## 📝 Comando de Emergencia

Si nada funciona, ejecutar manualmente cada hora con cron:

```bash
# En Render, agregar cron job
0 * * * * cd /opt/render/project/src && python test_celery_cloud.py
```

---

## 🎯 Solución Más Probable

**El problema más común es que Beat no está corriendo.**

**Verificar**:
1. Ir a Render dashboard
2. Buscar servicio "travelhub-beat"
3. Si no existe o está "Suspended", ese es el problema
4. Crear/reactivar el servicio Beat

**Comando de inicio correcto**:
```bash
celery -A travelhub beat --loglevel=info
```

---

**Última actualización**: 25 de Enero de 2025  
**Autor**: Amazon Q Developer
