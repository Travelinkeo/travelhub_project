# 🚑 QUICKSTART — Recuperación de emergencia

> **Cuándo usar:** el QR no aparece, el dashboard dice "404 Not Found", los mensajes no salen, o el flujo WhatsApp está roto.
> **Tiempo estimado:** 5–10 minutos.

---

## ⚡ Síntoma y diagnóstico rápido

```bash
# Paso 1 — ¿Tienes QR conectado? Si NO sigue con este doc.
docker exec travelhub_evolution node -e "
const http=require('http');
http.get('http://localhost:8080/instance/connect/<tu-slug>',
  {headers:{apiKey: process.env.AUTHENTICATION_API_KEY}}, r=>{
    let d=''; r.on('data',c=>d+=c); r.on('end',()=>{
      const j=JSON.parse(d);
      console.log('base64 length:', j.base64?j.base64.length:'NONE');
      console.log('pairingCode:', j.pairingCode||'none');
    });
  });"
```

| Resultado | Acción |
|-----------|--------|
| `base64 length: 0` o `NONE` | El contenedor Evolution NOQR — ir a paso **P1** |
| `base64 length: 13000+` | ✅ QR se genera. Problema está en Django — ir a paso **P2** |
| `ECONNREFUSED` | Evolution está caído — ir a paso **P3** |

`<tu-slug>` debe reemplazarse con `subdominio_slug` de la agencia, ej. `travelinkeo`, `viajero`, etc.

---

## P1 — Fix de WhatsApp (sin QR generado)

### P1.1 — Versión de WhatsApp

```bash
docker exec travelhub_evolution cat /evolution/.env | grep CONFIG_SESSION_PHONE_VERSION
```

**Debe decir exactamente:** `CONFIG_SESSION_PHONE_VERSION=2.3000.1035194821`

Si dice otra cosa:
```bash
docker exec travelhub_evolution sh -c \
  "sed -i 's/CONFIG_SESSION_PHONE_VERSION=.*/CONFIG_SESSION_PHONE_VERSION=2.3000.1035194821/' /evolution/.env && \
   grep CONFIG_SESSION_PHONE_VERSION /evolution/.env"
```

### P1.2 — Reiniciar Evolution

```bash
docker restart travelhub_evolution
# Esperar al menos 35s para que arranque Prisma + Baileys
```

Verificar en logs:
```bash
docker logs travelhub_evolution --tail 30 2>&1 | grep -E "tertiary|buildHash|connected to WA|Connection Terminated"
```

✅ **Esperado:**
```json
"appVersion":{"primary":2,"secondary":3000,"tertiary":1035194821}
"buildHash":"oslHHv+RCp4a5lmJCiiHLQ=="
```

❌ **Si ves `tertiary:1015901307`** → los parches manuales se borraron (contenedor reconstruido). Ver [`docs/03-PATCHES-EVOLUTION.md`](03-PATCHES-EVOLUTION.md).

### P1.3 — Forzar fetch de QR al cache Django

```bash
docker exec travelhub_web python3 /app/trigger_qr.py
```

✅ **Esperado:**
```
Evolution API: Instance 'travelhub' state is 'connecting'
Evolution QR cached via HTTP for travelhub
```

Si falla con `"Not Found"`:
```bash
# Verificar que la instance existe en Evolution
docker exec travelhub_evolution node -e "
const http=require('http');
http.post('http://localhost:8080/instance/create',
  '{\"instanceName\":\"<tu-slug>\",\"integration\":\"WHATSAPP-BAILEYS\",\"qrcode\":true}',
  {headers:{'Content-Type':'application/json','apiKey':process.env.AUTHENTICATION_API_KEY}}, r=>{
    let d=''; r.on('data',c=>d+=c); r.on('end',()=>console.log(d));
  });"
```

---

## P2 — Fix de Django (QR generado pero no se ve)

### P2.1 — Confirmar que Django tiene base64 en Redis

```bash
docker exec travelhub_broker redis-cli GET "django:default:evo_qr:<tu-slug>"
```

Si retorna base64 largo (12kb+) → ✅ cache lleno, refresca navegador con `Ctrl+Shift+R`.

Si retorna vacío → ir a P2.2.

### P2.2 — Forzar refresh desde Beat

Verifica que Celery Beat está corriendo:
```bash
docker ps --filter name=travelhub_beat --format "{{.Status}}"
# Debe ser: "Up X minutes (healthy)"
```

Si Beat no está activo:
```bash
docker compose restart celery_beat
```

### P2.3 — Verificar Celery Worker procesa tareas

```bash
docker logs travelhub_worker --tail 30 2>&1 | grep -i "qr\|fetch_evolution"
```

Si no hay logs de tareas QR → el worker está colgado. Verificar:
```bash
docker ps --filter name=travelhub_worker --format "{{.Status}}"
# Debe ser: "Up X minutes (healthy)"
```

### P2.4 — Verificar URL mapping en Django

> **Bugs conocidos:** `reverse("core:evolution_qr_proxy")` apunta al **Manager UI proxy** (el que da 404), no a la vista que sirve PNG. Debe ser `reverse("core:evolution_qr_image")`.

Verificar:
```bash
docker exec travelhub_web python3 -c "
from django.urls import reverse
print('qr_image  ->', reverse('core:evolution_qr_image', kwargs={'instance_name':'<tu-slug>'}))
print('qr_proxy  ->', reverse('core:evolution_qr_proxy', kwargs={'instance_name':'<tu-slug>'}))
"
```

✅ **Esperado:**
```
qr_image  -> /system/whatsapp/qr-img/<tu-slug>/
qr_proxy  -> /system/whatsapp/qr/<tu-slug>/
```

Si están al revés → alguien revirtió los fixes manuales. Reaplicar [`docs/04-FIXES-DJANGO.md`](04-FIXES-DJANGO.md).

---

## P3 — Fix de conectividad (Evolution caído)

### P3.0 — Usar el health-check dedicado

Antes de sufrir diagnosticando, usa el endpoint sin auth que acabamos de crear:

**Endpoint específico** (evalúa una sola agencia):
```bash
curl -s http://localhost:8000/system/whatsapp/health/<tu-slug>/ | jq
```

**Endpoint agregado** (evalúa todas las agencias):
```bash
curl -s http://localhost:8000/system/whatsapp/health/ | jq
```

**Interpretación del campo `status`:**
- `"ok"` → QR disponible en Redis cache O generable desde Evolution
- `"degraded"` → Evolution responde pero cache vacío (raro, debería regenerarse en segundos)
- `"down"` → Evolution caído, kill, o credenciales inválidas
- `"not_configured"` → Instancia en estado inicial (no debe pasar si la agencia fue creada correctamente)

**Interpretación del campo `checks.evolution_state`:**
- `"open"` ✅ → Conectado a WhatsApp
- `"connecting"` → Generando QR (probablemente funcionará)
- `"close"` → Instancia cerrada o ausente

Si `status: "down"`, ir a P3.1.

### P3.1 — Estado del contenedor

```bash
docker ps --filter name=travelhub_evolution --format "{{.Status}}"
```

| Estado | Acción |
|--------|--------|
| "Up" pero "Restarting" rápido | Loop de reinicios. Ver logs. |
| "Up X minutes (healthy)" | ✅ OK, ir a P1.1 |
| "Exited (1)" hace X min | Crash. Ver logs. |

### P3.2 — Logs en vivo

```bash
docker logs travelhub_evolution --tail 50 2>&1 | Select-String -Pattern "Error|error|FAIL|fail|traced"
```

### P3.3 — Healthcheck TCP

```bash
docker exec travelhub_evolution sh -c "ss -tln 2>/dev/null || netstat -tln 2>/dev/null" | grep ":8080"
# Debe mostrar: tcp LISTEN 0 ... *:8080
```

### P3.4 — Dependencias

```bash
# ffmpeg disponible?
docker exec travelhub_evolution which ffmpeg
# Esperado: /usr/bin/ffmpeg

# El parche existe?
docker exec travelhub_evolution cat /evolution/node_modules/@ffmpeg-installer/ffmpeg/index.js | head -15
# Debe contener: module.exports = { path: '/usr/bin/ffmpeg', ... }
```

Si falta → ver [`docs/03-PATCHES-EVOLUTION.md`](03-PATCHES-EVOLUTION.md) sección ffmpeg.

### P3.5 — Baileys está bien

```bash
docker exec travelhub_evolution node --check /evolution/node_modules/baileys/lib/Utils/generics.js
docker exec travelhub_evolution node --check /evolution/node_modules/baileys/lib/Utils/validate-connection.js
# Si hay SyntaxError → parches rotos. Ver docs/03.
```

### P3.6 — IP no bloqueada

```bash
docker exec travelhub_evolution node -e "
const https=require('https');
https.get('https://api.ipify.org?format=json', r=>{
  let d=''; r.on('data',c=>d+=c); r.on('end',()=>console.log(d));
});"
# Anota la IP (ej. 38.76.139.38)
```

Si WhatsApp rechaza TODAS las conexiones aunque versión es correcta, el problema puede ser **bloqueo de IP datacenter**. No hay solución sin proxy residential.

---

## ✅ Después de aplicar P1-P3

1. Limpia cache del navegador: `Ctrl+Shift+R`
2. Cierra sesión y re-loguéate
3. Espera 60 segundos para que Beat regenere cache
4. Si sigue roto → [`docs/01-INCIDENTE-CB-FAILURE-405.md`](01-INCIDENTE-CB-FAILURE-405.md) para análisis profundo

---

## Cuando el flujo funciona

```bash
# Confirmar TODO está OK
docker exec travelhub_web python3 -c "
from django.core.cache import cache
import requests, os
from django.conf import settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings.production')
import django
django.setup()

r = requests.get('http://localhost:8000/system/whatsapp/qr-img/<tu-slug>/',
                 cookies={'sessionid':'fake'}, allow_redirects=False)
print('Status:', r.status_code, '(esperado 302 por falta de auth, o 200 si authed)')
print('Cache hit:', bool(cache.get(f'evo_qr:<tu-slug>')))
" 2>&1 | tail -3
```
