# Anexo A — Endpoints relevantes Evolution + Django

> **Referencia rápida** de URLs y rutas usadas por el flujo WhatsApp.
> Útil para debugging cuando algo falla — comparar lo que el frontend pide vs. lo que Evolution devuelve.

---

## 📡 Evolution API v2.2.3 (atendai/evolution-api:latest)

| Método | Endpoint | ¿Sirve QR? | Notas |
|--------|----------|-------------|-------|
| `POST` | `/instance/create` | Indirectamente | Crea instancia; si `qrcode:true`, espera 2s + devuelve `qrcode.count` |
| `GET`  | `/instance/connect/<slug>` | ✅ **Sí** | **Endpoint correcto para QR**. Devuelve `{pairingCode, code, base64, count}` |
| `GET`  | `/instance/connectionState/<slug>` | No | Solo estado (`open` / `connecting` / `close`) |
| `GET`  | `/instance/fetchInstances` | No | Lista todas las instancias |
| `GET`  | `/manager/qr/<slug>/` | ⚠️ SPA | HTML 200 solo inicial. JS interno hace muchos fetch que NO existen en Evolution v2.2.3 → **404 Not Found** en navegador |
| `GET`  | `/instance/logout/<slug>` | No | DELETE equivalente |
| `DELETE` | `/instance/delete/<slug>` | No | Borra instancia |

### Diferencia crítica con v1

En Evolution v1, existía `/instance/qrcode/<slug>/` como endpoint dedicado para el QR PNG. **Esto NO existe en v2.2.3**. Si algún código viejo lo usa, devuelve 404.

---

## 🐍 Django — Endpoints del frontend

| URL | Nombre URL | Vista | Sirve | Notas |
|-----|-----------|-------|-------|-------|
| `/system/whatsapp/qr-img/<slug>/` | `core:evolution_qr_image` | `evolution_qr_proxy` | PNG | **Endpoint correcto**. Devuelve PNG inline desde Redis/Evolution |
| `/system/whatsapp/qr/<slug>/` | `core:evolution_qr_proxy` | `evolution_manager_proxy` | HTML | **Endpoint problemático.** Proxy al Evolution Manager UI (404 en v2.2.3). NO lo uses como fallback |
| `/system/whatsapp/qr/<slug>/<extra>` | `core:evolution_qr_assets` | `evolution_manager_proxy` | HTML | Assets estáticos (no funciona bien por cross-origin) |
| `/system/dashboard/whatsapp-qr/` | `bookings:whatsapp_qr` | `whatsapp_qr_view` | HTML partial | Vista HTMX. Refresca cada 30s |
| **`/system/whatsapp/health/`** | `core:evolution_qr_health` | `whatsapp_qr_health` | **JSON** | **Health-check. Sin auth. Para monitoring.** |
| **`/system/whatsapp/health/<slug>/`** | `core:evolution_qr_health_instance` | `whatsapp_qr_health` | **JSON** | Health-check específico |

### Trampa peligrosa de naming

```python
# CORRECTO — vista que sirve PNG
reverse("core:evolution_qr_image", kwargs={"instance_name": slug})
# → "/system/whatsapp/qr-img/<slug>/"

# PELIGROSO — vista que da 404 (proxy al Manager UI de Evolution v2.2.3)
reverse("core:evolution_qr_proxy", kwargs={"instance_name": slug})
# → "/system/whatsapp/qr/<slug>/"
```

**Verificación obligada tras cualquier deploy de urls_system.py:**
```bash
docker exec travelhub_web python3 -c "
from django.urls import reverse
print('image:', reverse('core:evolution_qr_image', kwargs={'instance_name':'X'}))
print('proxy:', reverse('core:evolution_qr_proxy', kwargs={'instance_name':'X'}))
"
```

---

## 📊 Response del `/system/whatsapp/health/<slug>/`

```json
{
  "service": "whatsapp-baileys",
  "instance": "travelhub",
  "timestamp": 1784513199,
  "checks": {
    "travelhub": {
      "instance": "travelhub",
      "status": "degraded",         // ← ok | degraded | down
      "checks": {
        "redis_cache": false,        // ¿Hay QR en Redis?
        "cache_age_seconds": null,
        "evolution_api_alive": true, // ¿Evolution responde?
        "evolution_state": "close",  // open | connecting | close
        "qr_generable": false         // ¿Puede generar QR nuevo ahora?
      }
    }
  },
  "overall_ms": 4168,
  "status": "degraded"
}
```

### Interpretación semántica

| Estado global | Causa probable | Acción |
|---------------|----------------|--------|
| `"ok"` | Cache lleno o Evolution QR listo | ✅ Todo bien |
| `"degraded"` | Evolution responde pero cache vacío | Esperar 60s para Beat, o refrescar manual |
| `"down"` | Evolution caído o credenciales mal | Revisar `travelhub_evolution` container + `WHATSAPP_MICROSERVICE_TOKEN` |
| `"not_configured"` | Instancia no inicializada | Llamar `EvolutionService.create_instance()` |

### Chequeos individuales

| Campo | Significado de `false` |
|-------|------------------------|
| `redis_cache` | El QR no está en Redis (probablemente Celery Beat no se ejecutó aún) |
| `evolution_api_alive` | Evolution no responde (revisar `docker ps`), o `WHATSAPP_MICROSERVICE_TOKEN` mal |
| `qr_generable` | Evolution responde pero instance state es `"close"` — crear la instancia primero |

---

## 🔄 Flujo de datos (actualizado)

```
Evolution (port 8080)
    ↓ /instance/connect/<slug>
[base64 PNG]  ← celula: 200ms

Django Service (via requests lib)
    ↓ Cache write 120s en Redis → {"evo_qr:<slug>": base64}
    ↓ INLINE al usuario como data:image/png;base64,...

HTML Template "whatsapp_qr_new.html"
    ↓ if "data:image" in qr_code → <img src="qr_code">
    ↓ else (fallback)     → <iframe src="/q...

Celery Beat (cada 60s)
    ↓ fetch_evolution_qr_task.delay(slug)
    ↓ Renueva Redis con QR fresco

HTMX (cada 30s en dashboard)
    ↓ trigger /system/dashboard/whatsapp-qr/
    ↓ refresca qr_code
```

---

## 🐛 Endpoints que dan 404 en Evolution v2.2.3 (NO USAR)

Estos endpoints eran comunes en v1 o intentan usar paths de Manager UI. **Todos devuelven 404**:

```
GET  /instance/qrcode/<slug>/                              ← v1
GET  /instance/qrcode/base64/<slug>/
GET  /instance/qrcode/base64/<slug>/
POST /qr/
GET  /api/v2/instance/<slug>/qrcode
```

Si algún código los usa, hay que migrar a `/instance/connect/<slug>` que es el único soportado en v2.2.3.
