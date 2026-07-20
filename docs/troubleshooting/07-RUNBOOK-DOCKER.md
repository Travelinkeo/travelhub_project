# 🐳 RUNBOOK — Deploy manual de cambios al contenedor `travelhub_web`

> **Cuándo usar:** modificas un archivo `.py` en tu máquina host y quieres verlo reflejado en el contenedor **sin** ejecutar `docker compose build` (que tarda minutos).
>
> **Limitación:** este método funciona **sólo para cambios en archivos `.py` y templates `.html`**. Para cambios en `package.json`, dependencias npm, etc. **debes reconstruir la imagen**.

---

## ⚠️ Por qué es diferente a lo normal

En este proyecto, **el servicio Django (`travelhub_web`) NO tiene volume-bind al directorio del código fuente** en `docker-compose.yml`. El código se copia al construir la imagen Docker:

```dockerfile
# Dockerfile (líneas relevantes)
COPY travelhub/ ./travelhub/
COPY core/ ./core/
COPY apps/ ./apps/
```

Eso significa que:
- Los contenedores tienen una **copia estática** del código al momento del build
- `docker restart` NO actualiza el código (sigue congelado)
- `docker exec` puede modificar archivos pero **gunicorn con `--preload` ya cargó los módulos al arranque** — los cambios no surten efecto hasta el reload

---

## 🚀 Procedimiento paso a paso

### 1. Ejecuta el script de deploy

```bash
# Asumes que ya modificaste archivos en tu host
bash ./deploy_local_changes.sh
```

El script:
1. Hace `docker cp` de cada archivo modificado a su ubicación en `/app/`
2. Limpia `__pycache__` y archivos `.pyc`
3. Envía `SIGHUP` al master de gunicorn (PID variable)
4. Si SIGHUP falla, reinicia el contenedor con `docker restart`

### 2. Verifica el reload

```bash
# Buscar el HUP procesado en logs
docker logs travelhub_web 2>&1 | grep "Hang up" | tail -2
# Esperado:
# [2026-07-19 21:50:38 -0400] [102] [INFO] Handling signal: hup
# [2026-07-19 21:50:38 -0400] [102] [INFO] Hang up: Master

# Verificar que gunicorn está sirviendo (4 workers)
docker exec travelhub_web sh -c "ps 2>/dev/null | head -20" 2>&1 | grep gunicorn
```

### 3. Verifica que tu cambio quedó cargado

```python
# Conectar manualmente al contenedor y verificar
docker exec travelhub_web python3 -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'travelhub.settings.production')
import django
django.setup()
from core.views.evolution_qr_view import whatsapp_qr_health
print('whatsapp_qr_health:', whatsapp_qr_health.__name__)
"
# Esperado: whatsapp_qr_health: whatsapp_qr_health
```

---

## ⚠️ Casos donde el reload NO funciona

### Cambios en `urls_system.py`

Nuevo path = cambios en `urlpatterns`. A veces gunicorn no re-recarga URLs. Solución:

```bash
docker exec travelhub_web sh -c "find /app -name '__pycache__' -exec rm -rf {} +"
docker restart travelhub_web
```

### Cambios en `models.py`

Schema migrations + DB changes → **no** usar este script. Requiere:

```bash
docker exec travelhub_web python3 manage.py makemigrations
docker exec travelhub_web python3 manage.py migrate
```

### Cambios en archivos estáticos (CSS/JS)

```bash
docker exec travelhub_web python3 manage.py collectstatic --noinput
docker restart travelhub_web
```

---

## 🐛 Troubleshooting del reload

| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Cambio no surte efecto, gunicorn sin errores | `__pycache__` sin limpiar | `find /app -name "__pycache__" -exec rm -rf {} +` |
| `HUP: Permiso denegado` | El proceso de gunicorn lo ejecuta `appuser`, no `root` | El script ya maneja esto |
| Container restartloop tras `docker restart` | DB no disponible, o `pgbouncer` no levantado | Esperar 30s y ver los logs |
| Output: `KeyError('algo')` tras deploy | Caché Vuex/React cargado en navegador | `Ctrl+Shift+R` |

---

## 🔄 Alternativa: build completo (cuando el reload falla)

```bash
# 1. Build (tarda 1-3 minutos)
docker compose build web

# 2. Recrear contenedor
docker compose up -d web

# 3. Verificar health
sleep 30 && docker ps --filter name=travelhub_web --format "{{.Status}}"
```

**Ventaja:** confiable
**Desventaja:** destruye cambios manuales al contenedor (como patches de Evolution `node_modules/`)

---

## 📜 Comandos de diagnóstico rápido

```bash
# ¿Qué archivos cambié en el host?
git diff --name-only HEAD~5 -- '*.py' '*.html'

# ¿Gunicorn cargó mis cambios?
docker exec travelhub_web python3 -c "
import inspect
from core.views import evolution_qr_view
src = inspect.getsource(evolution_qr_view)
print('has whatsapp_qr_health:', 'whatsapp_qr_health' in src)
"

# ¿Qué PID corre gunicorn?
docker exec travelhub_web sh -c "
  for p in /proc/[0-9]*; do
    pid=\${p##*/}
    cmd=\$(tr '\\0' ' ' < \$p/cmdline 2>/dev/null | head -c 80)
    echo \$cmd | grep -q gunicorn && echo \"PID \$pid: \$cmd\"
  done
"
```

---

> **TL;DR:** El script `deploy_local_changes.sh` automatiza los 4 pasos manuales (cp + clear cache + HUP + verify). Para 95% de los cambios es suficiente. Para el resto, `docker compose build web && docker compose up -d web`.
