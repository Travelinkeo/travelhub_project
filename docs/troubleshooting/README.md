# 📱 WhatsApp Baileys QR — Troubleshooting & Recovery Guide

> **Propósito:** Este directorio contiene toda la documentación acumulada durante la resolución del bug "QR code no aparece / 404 Not Found al refrescar" en la integración entre `TravelHub Pro` y `Evolution API v2.2.3` (con WhatsApp vía Baileys).
> **Si la integración vuelve a fallar:** seguir el [quickstart en `00-QUICKSTART.md`](00-QUICKSTART.md).
> **Para entender el bug raíz:** leer [`01-INCIDENTE-CB-FAILURE-405.md`](01-INCIDENTE-CB-FAILURE-405.md).

---

## 🔍 Endpoint health-check (julio 2026)

El sistema expone un endpoint **sin auth** para monitoring:

```bash
curl -s http://localhost:8000/system/whatsapp/health/travelhub/ | jq
# o para todas las agencias:
curl -s http://localhost:8000/system/whatsapp/health/ | jq
```

Devuelve JSON con:
- `status`: `ok` | `degraded` | `down`
- `checks.evolution_state`: estado de la conexión a WhatsApp
- `checks.redis_cache`: si hay QR en cache
- `checks.qr_generable`: si Evolution puede generar uno nuevo

Para integrar con UptimeRobot/Prometheus/Datadog — usar `status` como criterio de alerta. Ver [`07-RUNBOOK-DOCKER.md`](07-RUNBOOK-DOCKER.md) sección P3.0.

---

## 📑 Índice de documentos

| # | Documento | Contenido | Cuándo leerlo |
|---|-----------|-----------|---------------|
| **00** | [`00-QUICKSTART.md`](00-QUICKSTART.md) | Checklist de recuperación rápida (3 pasos) | **PRIMERO cuando el QR no aparece** |
| **01** | [`01-INCIDENTE-CB-FAILURE-405.md`](01-INCIDENTE-CB-FAILURE-405.md) | Diagnóstico completo del incidente original (CB:failure 405 / Connection Terminated) | Para entender QUÉ falló y POR QUÉ |
| **02** | [`02-CAUSAS-RAIZ.md`](02-CAUSAS-RAIZ.md) | Las 4 causas raíz identificadas con profundización | Para entender todas las capas del problema |
| **03** | [`03-PATCHES-EVOLUTION.md`](03-PATCHES-EVOLUTION.md) | Los 6 parches manuales al contenedor Evolution | Cuando se reconstruye el contenedor y hay que reaplicarlos |
| **04** | [`04-FIXES-DJANGO.md`](04-FIXES-DJANGO.md) | Los 5 cambios al código Django | Cuando el QR aparece pero el iframe muestra 404 |
| **05** | [`05-ROMPIENDO-CACHE.md`](05-ROMPIENDO-CACHE.md) | Por qué el cache de Redis es frágil y cómo hacerlo robusto | Para entender la cadena de cache: Evolution → Django → Celery |
| **06** | [`06-CHECKLIST-MANTENIMIENTO.md`](06-CHECKLIST-MANTENIMIENTO.md) | Tareas de mantenimiento preventivo | Cuando se quiera PREVENIR la recurrencia |
| **07** | [`07-RUNBOOK-DOCKER.md`](07-RUNBOOK-DOCKER.md) | Deploy manual de cambios `.py` sin rebuild | Cuando modificas Django y no quieres esperar build |
| **A** | [`APENDICE-A-ENDPOINTS.md`](APENDICE-A-ENDPOINTS.md) | Tabla de endpoints Evolution + Django relevantes (incluido health-check) | Referencia rápida de URLs y rutas |
| **B** | [`APENDICE-B-VERSIONES.md`](APENDICE-B-VERSIONES.md) | Versiones, hashes y checksums | Verificar que los parches se aplicaron correctamente |

---

## 🚨 TL;DR de emergencia

Si el QR no aparece (`404 Not Found` o nada):

```bash
# 1. Versión de WhatsApp correcta en .env del contenedor Evolution
docker exec travelhub_evolution sh -c "grep CONFIG_SESSION_PHONE_VERSION /evolution/.env"
# Debe decir: CONFIG_SESSION_PHONE_VERSION=2.3000.1035194821
# Si dice otra cosa: ver docs/00-QUICKSTART.md paso 1

# 2. Comprobar conexión real
docker exec travelhub_evolution node -e "
const http=require('http');
http.get('http://localhost:8080/instance/connect/<slug-agencia>',
  {headers:{apiKey: process.env.AUTHENTICATION_API_KEY}}, r=>{
    let d=''; r.on('data',c=>d+=c); r.on('end',()=>console.log(d.substring(0,300)));
  });"

# 3. Forzar regenerar cache de QR
docker exec travelhub_web python3 /app/trigger_qr.py
```

Si esto NO funciona → leer [`docs/00-QUICKSTART.md`](00-QUICKSTART.md) completo.

---

## 📚 Lecciones aprendidas (resumen ejecutivo)

1. **`CONFIG_SESSION_PHONE_VERSION` en `.env` es la fuente de verdad** sobre qué versión del protocolo WhatsApp se usa. Si queda hardcoded en una versión vieja, todo falla con `CB:failure 405` o `Connection Terminated by Server`.

2. **El proceso de Evolution tarda ~60s en arrancar** (migrations Prisma + generación del cliente). Hay que esperar pacientemente: `sleep 30` + `docker logs tail` después de cualquier reinicio.

3. **Naming de URL invertida en `urls_system.py`:** el nombre `evolution_qr_proxy` apunta al **Evolution Manager UI proxy** (da 404), mientras `evolution_qr_image` apunta a la vista que sirve PNG real. Mezclar estos nombres = iframe roto.

4. **Cache de 3 tiempos:** Redis (TTL 120s) ← Celery Beat task (cada 60s) ← Evolution (regenera QR cada 60s). Si cualquiera de los 3 falla, iframe queda vacío.

5. **El contenedor `atendai/evolution-api:latest` está incompleto en dependencias:** `@ffmpeg-installer/linux-x64` NO viene pre-instalado; hay que parchear `@ffmpeg-installer/ffmpeg/index.js` para usar `/usr/bin/ffmpeg` del sistema.

6. **Hay 5 copias de Baileys en `node_modules`** por culpa de restorations de npm: `baileys/`, `@whiskeysockets/baileys/`, y 3 en `.baileys-*` directorios cache. La versión "extra" aparece si npm se vuelve a ejecutar. **No tocar node_modules con npm**.

---

## Estado actual (julio 2026)

- **Versión WhatsApp en uso:** `2.3000.1035194821` (md5 hash `oslHHv+RCp4a5lmJCiiHLQ==`)
- **Baileys:** CJS 6.17.16 (parcheado en runtime para que `appVersion.tertiary = 1035194821` directamente en `getUserAgent`)
- **Contenedor Evolution:** funcional con 6 parches manuales
- **Contenedor Django:** patches en código (5 archivos modificados)
- **Celery Beat:** ejecutándose cada 60s para mantener cache caliente
- **QR disponible:** ✅ Se genera correctamente y se persiste en Redis (TTL 120s)

---

## ⚠️ Limitaciones conocidas

- **El QR de WhatsApp expira cada ~60 segundos**. Después de 1 minuto desde que se muestra, hay que escanearlo RÁPIDO o pedir uno nuevo. Si expira, el contenedor Evolution lo regenera automáticamente al siguiente `cache miss`.

- **Si el contenedor Evolution se RECONSTRUYE desde la imagen Docker**, los 6 parches manuales en `node_modules/` se pierden. Ver [`docs/03-PATCHES-EVOLUTION.md`](03-PATCHES-EVOLUTION.md) para reaplicarlos.

- **Hay un único IP de salida (`38.76.139.38`)**. Si WhatsApp bloquea este rango, ya no tenemos túnel VPN/residential para escalar. Considerar un futuro: configurar proxy rotativo.

- **El login del supervisor de Django usa `gunicorn --preload`** sin `--reload`, así que cualquier cambio al código Django requiere `docker restart travelhub_web` (no basta con `docker restart`).

---

> **Si este directorio te ha ahorrado horas de debug:** me alegro. Si descubres algo nuevo, **actualízalo inmediatamente** para no perder la pista la próxima vez.
