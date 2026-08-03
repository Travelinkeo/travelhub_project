# ConfiguraciÃ³n de Tareas Programadas con cron-job.org (GRATIS)

## ðŸŽ¯ Reemplazo de Celery Beat sin costo

En lugar de pagar por workers de Celery en Render, usamos **cron-job.org** para llamar endpoints HTTP.

---

## ðŸ“‹ Paso 1: Obtener Token de Seguridad

El token es los primeros 32 caracteres de tu `SECRET_KEY` de Render.

1. Ve a https://dashboard.render.com
2. Selecciona tu servicio "travelhub"
3. Ve a "Environment"
4. Copia el valor de `SECRET_KEY`
5. Toma los primeros 32 caracteres

**Ejemplo**: Si SECRET_KEY es `abc123def456...xyz`, tu token es `abc123def456...` (32 chars)

---

## ðŸ“‹ Paso 2: Crear Cuenta en cron-job.org

1. Ve a https://cron-job.org/en/signup/
2. Crea cuenta gratuita (permite hasta 50 cron jobs)
3. Verifica tu email

---

## ðŸ“‹ Paso 3: Configurar Tareas Programadas

### Tarea 1: Sincronizar Tasa BCV (Diario 9:00 AM)

1. Click "Create cronjob"
2. **Title**: `TravelHub - Sincronizar BCV`
3. **URL**: `https://travelhub.cc/api/cron/sincronizar-bcv/?token=TU_TOKEN_AQUI`
4. **Schedule**:
   - Type: `Every day`
   - Time: `09:00` (UTC-4 = 9:00 AM Venezuela)
5. **Notifications**: Email on failure
6. Click "Create cronjob"

### Tarea 2: Recordatorios de Pago (Diario 10:00 AM)

1. Click "Create cronjob"
2. **Title**: `TravelHub - Recordatorios Pago`
3. **URL**: `https://travelhub.cc/api/cron/recordatorios-pago/?token=TU_TOKEN_AQUI`
4. **Schedule**:
   - Type: `Every day`
   - Time: `10:00` (UTC-4)
5. Click "Create cronjob"

### Tarea 3: Cierre Mensual (DÃ­a 1 de cada mes, 2:00 AM)

1. Click "Create cronjob"
2. **Title**: `TravelHub - Cierre Mensual`
3. **URL**: `https://travelhub.cc/api/cron/cierre-mensual/?token=TU_TOKEN_AQUI`
4. **Schedule**:
   - Type: `Every month`
   - Day: `1`
   - Time: `02:00` (UTC-4)
5. Click "Create cronjob"

---

## ðŸ” Verificar que Funciona

### Test Manual

Abre en tu navegador (reemplaza TU_TOKEN):

```
https://travelhub.cc/api/cron/health/
```

DeberÃ­as ver:
```json
{"status": "ok", "service": "travelhub"}
```

### Test con Token

```
https://travelhub.cc/api/cron/sincronizar-bcv/?token=TU_TOKEN_AQUI
```

DeberÃ­as ver:
```json
{"status": "success", "message": "Tasa BCV sincronizada"}
```

---

## ðŸ“Š Endpoints Disponibles

| Endpoint | DescripciÃ³n | Frecuencia Recomendada |
|----------|-------------|------------------------|
| `/api/cron/sincronizar-bcv/` | Actualiza tasa BCV | Diario 9:00 AM |
| `/api/cron/recordatorios-pago/` | EnvÃ­a recordatorios | Diario 10:00 AM |
| `/api/cron/cierre-mensual/` | Cierre contable | Mensual dÃ­a 1, 2:00 AM |
| `/api/cron/health/` | Health check | Cada 5 min (opcional) |

---

## ðŸ”’ Seguridad

- âœ… Token requerido en todos los endpoints (excepto health)
- âœ… Token es Ãºnico por instalaciÃ³n (SECRET_KEY)
- âœ… Sin token = Error 403 Forbidden
- âœ… Logs de acceso en Render

---

## ðŸ’° Costo

**$0/mes** - cron-job.org es completamente gratuito para hasta 50 cron jobs.

---

## ðŸ†š ComparaciÃ³n con Celery

| Aspecto | Celery Beat | cron-job.org |
|---------|-------------|--------------|
| **Costo** | ~$14/mes (2 workers) | $0 |
| **ConfiguraciÃ³n** | Compleja | Simple |
| **Mantenimiento** | Alto | Bajo |
| **Confiabilidad** | Alta | Alta |
| **LÃ­mite de tareas** | Ilimitado | 50 gratis |

---

## ðŸ“ Notas

- **Zona horaria**: cron-job.org usa UTC. Venezuela es UTC-4.
- **Render sleep**: Plan gratuito duerme despuÃ©s de 15 min. El primer cron job lo despertarÃ¡ (puede tardar 30 seg).
- **Notificaciones**: Configura email en cron-job.org para recibir alertas de fallos.

---

**Ãšltima actualizaciÃ³n**: 26 de Enero de 2025
