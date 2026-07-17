# Plan de Remediacion — TravelHub SaaS

> **Auditado contra codigo real:** 2026-07-16
> **Rama activa:** `hardening/operational-risks @ 6248d08`
> **Criterio de prioridad:** CVSS adaptado al contexto SaaS multi-tenant

---

## Resumen ejecutivo

De los 14 puntos de deuda tecnica catalogados en `CONTEXT_MAP.md ss10`,
la auditoria en codigo confirma que:

- HECHO **8 ya estan resueltos** en el codigo actual (verificado linea a linea)
- PARCIAL **4 estan parcialmente resueltos** (fix presente pero incompleto o con condicion residual)
- ABIERTO **2 siguen abiertos** sin ningun fix implementado

La auditoria tambien corrije el conteo del CONTEXT_MAP: el mapa de meses GDS
esta duplicado en **5 archivos** (no 4 como estaba documentado).

---

## Tabla de estado verificado (auditoria 2026-07-16)

| ID | Descripcion | Estado real en codigo | Sprint |
|---|---|---|---|
| P0-002 | IDOR BoletoRetryParseAPIView | HECHO — `get_object_tenant_or_404()` en boleto_views.py:167 | — |
| P0-003 | IDOR VentaDoubleInvoiceAPIView | HECHO — `get_object_tenant_or_404(Venta, agencia)` en boleto_views.py:365 | — |
| P0-006 | Traceback expuesto en respuesta 500 | HECHO — `error_id` + `logger.exception()`, sin `str(e)` | — |
| P1-001 | Doble signal `post_save` BoletoImportado | HECHO — senial unica consolidada (comentario P1-001 en signals.py:36) | — |
| P1-003 | PgBouncer + CONN_MAX_AGE fuga RLS | HECHO — `USE_PGBOUNCER` condicional en base.py:221-224 | — |
| P1-004 | Cache agencia TTL=120s | HECHO — reducido a 30s + `invalidate_all_agency_caches()` en security.py:43 | — |
| P1-006 | UniversalAIParser truncado silencioso | HECHO — `logger.warning` + flag `_text_was_truncated` en ai_universal_parser.py:90-98 | — |
| P2-004 | celery.py default `settings.production` | HECHO — default cambiado a `travelhub.settings.development` en celery.py:12 | — |
| P1-007 | `_send_factura_whatsapp` `.apply()` sincrono | HECHO — usa `.delay()` con try/except en signals.py:239-242 | — |
| P2-002 | Archivos debug en raiz con credenciales | HECHO — no hay archivos debug_* ni temp_* en raiz (solo scratch/ y scratch_scripts/) | — |
| P1-002 | celery.py importa `settings` a nivel de modulo | PARCIAL — `django.setup()` no aparece pero `from django.conf import settings` en linea 5 puede causar AppRegistryNotReady en tests | Sprint 1 |
| P1-005 | `locale.setlocale` monkey patch doble | PARCIAL — dos implementaciones paralelas: `core/locale_patch.py` + `travelhub/__init__.py:12-30`. Riesgo de doble wrap | Sprint 1 |
| P2-006 | `AgenciaManager` parsea `sys.argv` en cada query | PARCIAL — constante de modulo en base.py:9-15 pero 3 usos inline residuales en lineas 134, 136, 260 | Sprint 2 |
| P2-005 | Mapa de meses GDS duplicado | PARCIAL — **5 archivos** con definicion independiente (kiu_parser.py, web_receipt_parser.py:1238, receipt_parsers/utils.py, pnr_parser_service.py, ai_schemas.py) | Sprint 2 |

### Integraciones incompletas abiertas

| Item | Estado | Sprint |
|---|---|---|
| PWA cache offline (service worker) | ABIERTO — service-worker.js sin estrategia de cache | Sprint 3 |
| i18n espanol (42/300+ entradas) | ABIERTO — sin traducciones suficientes | Sprint 3 |
| CSP `unsafe-eval` en admin (Alpine.js) | DOCUMENTADO — pendiente migracion `@alpinejs/csp-bundle`, linea middleware.py:377 | Sprint 3 |
| SSO sso_callback flow completo | NO VERIFICADO — modelo y views existen pero flow end-to-end no auditado | Sprint 3 |

---

## Sprint 1 — Deuda Tecnica Residual de Estabilidad
**Estimado:** 2-4 horas
**Impacto:** Eliminar condiciones residuales que afectan CI y comportamiento de workers

---

### S1-A — Eliminar doble implementacion de locale patch

**Problema:** `core/locale_patch.py` y `travelhub/__init__.py:12-30` implementan el mismo
monkey patch sobre `locale.setlocale` por separado. Cuando Django carga
`CoreConfig.ready()` despues de `__init__.py`, el patch se aplica dos veces de
forma anidada, envolviendo la funcion ya parchada y causando depth de llamadas
innecesario y logs confusos.

**Archivos afectados:**
- `travelhub/__init__.py` — lineas 12-30 (eliminar bloque)
- `core/locale_patch.py` — agregar guard anti-doble-patch

**Accion:**

1. Eliminar el bloque de patch de `travelhub/__init__.py` (lineas 12-30).
2. Agregar guard `_is_safe_patch` en `core/locale_patch.py`:

```python
# core/locale_patch.py — version final con guard
import locale
import logging

logger = logging.getLogger(__name__)

def apply_locale_patch():
    """Aplica patch seguro a locale.setlocale. Idempotente (doble llamada = no-op)."""
    if getattr(locale.setlocale, "_is_safe_patch", False):
        logger.debug("locale.setlocale ya parchado, omitiendo doble patch.")
        return

    original_setlocale = locale.setlocale

    def safe_setlocale(category, locale_str=None):
        try:
            return original_setlocale(category, locale_str)
        except locale.Error:
            logger.warning(f"[SRE L3] locale '{locale_str}' no soportado. Usando C.UTF-8.")
            return original_setlocale(category, "C.UTF-8")

    safe_setlocale._is_safe_patch = True  # guard anti-doble-patch
    locale.setlocale = safe_setlocale
    logger.info("[SRE L3] locale.setlocale monkey patch aplicado.")
```

**Verificacion:**
```bash
python -c "
import locale
from core.locale_patch import apply_locale_patch
apply_locale_patch()
apply_locale_patch()  # segunda llamada debe ser no-op
assert getattr(locale.setlocale, '_is_safe_patch', False)
print('OK: guard funciona correctamente')
"
```

---

### S1-B — Aislar importacion de settings en celery.py

**Problema:** `travelhub/celery.py:5` importa `from django.conf import settings` al nivel
de modulo. Si un test importa este modulo antes de que `django.setup()` se complete
(ej: fixtures, conftest.py), puede causar `AppRegistryNotReady` esporadicamente.

**Archivo afectado:** `travelhub/celery.py`

**Accion:** Mover la importacion de `settings` dentro del bloque de carga del beat
schedule y protegerlo con try/except:

```python
# travelhub/celery.py — reemplazar bloque de carga de beat schedule (lineas 57-71)

# Cargar CELERY_BEAT_SCHEDULE — import de settings diferido para evitar
# AppRegistryNotReady si celery.py se importa antes de django.setup()
_beat_schedule = None
try:
    from django.conf import settings as _dj_settings
    _beat_schedule = getattr(_dj_settings, "CELERY_BEAT_SCHEDULE", None)
except Exception:
    pass  # Django no esta configurado aun; usamos fallback

if _beat_schedule is None:
    try:
        from travelhub.celery_beat_schedule import CELERY_BEAT_SCHEDULE as _beat_schedule
        logger.info("CELERY_BEAT_SCHEDULE cargado desde celery_beat_schedule.py")
    except ImportError:
        _beat_schedule = {}
        logger.warning("No se encontro CELERY_BEAT_SCHEDULE. Beat sin tareas programadas.")

app.conf.beat_schedule = _beat_schedule
```

**Verificacion:**
```bash
python -m pytest apps/ --co -q 2>&1 | grep -i "appregistr"
# Debe retornar 0 lineas (sin errores)
```

---

## Sprint 2 — Deuda de Calidad de Codigo
**Estimado:** 3-5 horas
**Impacto:** Reducir overhead de CPU, eliminar 4 definiciones duplicadas y riesgo de divergencia

---

### S2-A — Centralizar mapa de meses GDS (P2-005 corregido: 5 archivos)

**Problema:** El mapa de meses GDS (ENE, FEB, MAR...) tiene **5 definiciones independientes**
en el proyecto. Si una aerolinea usa una abreviatura alternativa (ej: AGO vs AUG en
boletos Avior), hay que actualizarlo en 5 lugares con riesgo de divergencia.

**Archivos con definicion duplicada (eliminar y reemplazar por import):**
- `apps/automation/parsers/kiu_parser.py`
- `apps/automation/parsers/legacy/web_receipt_parser.py:1238`
- `apps/automation/parsers/receipt_parsers/utils.py`
- `apps/bookings/services/pnr_parser_service.py`
- `core/models/ai_schemas.py`

**Fuente de verdad (mantener):**
- `apps/automation/parsers/normalization.py` — verificar que exporta la constante

**Accion:**

1. Verificar que `normalization.py` expone `GDS_MONTH_MAP` como constante de modulo:
```bash
python -c "from apps.automation.parsers.normalization import GDS_MONTH_MAP; print(list(GDS_MONTH_MAP.items())[:3])"
```

2. Si el nombre es diferente, definir un alias exportado:
```python
# apps/automation/parsers/normalization.py (agregar al final)
# Alias para compatibilidad con importaciones existentes
GDS_MONTH_MAP = MESES_GDS  # o el nombre real de la constante
```

3. En cada archivo con definicion duplicada, reemplazar por:
```python
# ELIMINAR el dict local meses_gds = {"ENE": "01", ...}

# AGREGAR al inicio del archivo:
from apps.automation.parsers.normalization import GDS_MONTH_MAP as meses_gds
```

4. Ejecutar tests de regresion de parsing:
```bash
python -m pytest apps/automation/tests/ apps/bookings/tests/ -k "parser or boleto" -v
```

**Verificacion:**
```bash
python -c "
import subprocess, sys
result = subprocess.run(['grep', '-rn', r'meses_gds\s*=\s*{', 'apps/', 'core/'], capture_output=True, text=True)
count = len([l for l in result.stdout.splitlines() if l.strip()])
print(f'Definiciones inline restantes: {count}')
assert count == 0, 'Aun hay definiciones duplicadas'
print('OK: mapa de meses centralizado')
"
```

---

### S2-B — Completar optimizacion sys.argv en AgenciaManager (P2-006)

**Problema:** `core/models/base.py:9-15` define correctamente una constante de modulo
`_IS_MANAGEMENT_COMMAND`, pero hay 3 usos residuales de `sys.argv` inline que se
evaluan en runtime en las lineas 134, 136 y 260.

**Archivo afectado:** `core/models/base.py`

**Accion:** Reemplazar los 3 usos inline por la constante ya definida:

```python
# ANTES (linea ~134):
if (
    sys.argv
    and sys.argv[0].endswith("manage.py")
    and any(arg in sys.argv for arg in ["makemigrations", "migrate", ...])
):

# DESPUES:
if _IS_MANAGEMENT_COMMAND:
```

```python
# ANTES (linea ~260):
if "manage.py" in sys.argv and "test" in sys.argv:

# DESPUES:
if _IS_MANAGEMENT_COMMAND:
```

**Impacto de performance:** Eliminar ~2-3 comparaciones de lista O(n) por cada
llamada a `.objects.all()`, `.objects.filter()`, etc. En una pagina con 20 queries
= 40-60 comparaciones de lista innecesarias por request.

**Verificacion:**
```bash
python -c "
import ast, pathlib
src = pathlib.Path('core/models/base.py').read_text()
tree = ast.parse(src)
# Contar accesos a sys.argv fuera de la definicion de constante
print('Verificar manualmente que solo queda 1 uso (definicion de _IS_MANAGEMENT_COMMAND)')
"

# Verificacion rapida:
grep -n "sys.argv" core/models/base.py
# Debe retornar solo las lineas 9-15 (definicion de la constante)
```

---

## Sprint 3 — Integraciones Incompletas
**Estimado:** 8-16 horas
**Impacto:** Feature completeness y hardening de seguridad en frontend

---

### S3-A — PWA: Implementar estrategia de cache en Service Worker

**Problema:** Las rutas `/manifest.json` y `/service-worker.js` existen en `urls.py` pero
el service worker probablemente es un stub sin estrategia de cache. Sin cache, la PWA
no funciona offline y puede interferir con el cache del browser.

**Archivos afectados:**
- `core/views/pwa_views.py` — leer completo antes de modificar
- `core/templates/` o `static/` — buscar sw.js actual

**Paso previo (lectura):**
```bash
python -c "
import pathlib
pwa = pathlib.Path('core/views/pwa_views.py').read_text()
print(pwa[:2000])  # ver que devuelve service_worker()
"
```

**Estrategia a implementar:**

```javascript
// service-worker.js — estrategia Network-First para API + Cache-First para estaticos
const CACHE_NAME = 'travelhub-v2';
const STATIC_ASSETS = [
    '/static/css/main.css',
    '/static/js/main.js',
    '/offline/'
];
const API_PREFIXES = ['/api/', '/health/', '/finance/'];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME)
            .then(c => c.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (e) => {
    // Purgar caches viejos al activar nueva version
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
});

self.addEventListener('fetch', (e) => {
    const isAPI = API_PREFIXES.some(p => e.request.url.includes(p));
    if (isAPI) {
        // Network-First: intentar red, caer a cache, caer a offline
        e.respondWith(
            fetch(e.request)
                .catch(() => caches.match(e.request))
                .catch(() => caches.match('/offline/'))
        );
    } else {
        // Cache-First: servir desde cache, actualizar en background
        e.respondWith(
            caches.match(e.request)
                .then(r => r || fetch(e.request).then(res => {
                    const clone = res.clone();
                    caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
                    return res;
                }))
        );
    }
});
```

**Verificacion:** Chrome DevTools > Application > Service Workers — confirmar registro,
cache poblado y modo offline funciona.

---

### S3-B — Migrar Alpine.js a CSP-bundle para eliminar unsafe-eval

**Problema:** `core/middleware.py:375-379` documenta que `/admin/` y `/system/` incluyen
`'unsafe-eval'` porque Alpine.js vanilla lo requiere. Esto debilita la CSP de todas
las paginas admin, habilitando eval() para codigo JS inyectado.

**Proceso de migracion segura (en 3 fases):**

**Fase 1 — Report-Only (sin romper produccion):**
1. Agregar temporalmente header `Content-Security-Policy-Report-Only` con la CSP sin `unsafe-eval`.
2. Monitorear violaciones en `/csp-report/` durante 48-72h.

**Fase 2 — Correccion:**
3. Identificar todos los templates que usan Alpine.js:
```bash
grep -rn "alpinejs\|x-data\|x-on:" templates/ static/ --include="*.html" --include="*.js"
```
4. Reemplazar el bundle de Alpine por `@alpinejs/csp`:
```html
<!-- ANTES -->
<script defer src="cdn.alpinejs.net/3.x.x/cdn.min.js"></script>

<!-- DESPUES: Alpine CSP-compatible -->
<script defer src="cdn.alpinejs.net/3.x.x/module.esm.js" type="module"></script>
```
5. En `core/middleware.py`, eliminar `'unsafe-eval'` del bloque `/admin/` y `/system/`.

**Fase 3 — Enforcement:**
6. Cambiar de `Report-Only` a `Content-Security-Policy` real.
7. Monitorear violaciones CSP en las primeras 24h post-deploy.

**Verificacion:**
```bash
curl -I https://travelhub.cc/admin/ | grep "Content-Security-Policy"
# El valor no debe contener 'unsafe-eval'
```

---

### S3-C — i18n: Completar traducciones al espanol

**Problema:** Solo 42 de ~300+ strings estan traducidas al espanol. El sistema muestra
mensajes en ingles a usuarios de agencias venezolanas.

**Accion:**

1. Regenerar strings pendientes:
```bash
python manage.py makemessages -l es --no-wrap
```

2. Usar Gemini para primera pasada automatica (aprovechando AIEngine existente):
```python
# scratch_scripts/translate_po.py
import pathlib
from apps.automation.services.ai_engine import AIEngine

engine = AIEngine()
po_file = pathlib.Path("locale/es/LC_MESSAGES/django.po")
# Leer, extraer msgid con msgstr vacios, llamar Gemini batch
# El script completo se crea en Sprint 3
```

3. Revisar manualmente terminos de dominio venezolano:
   - IGTF, VEN-NIF, PNR, Consolidador, Tarifario, Diferencial Cambiario
   - Nombres de estados: confirmado, pendiente, anulado, por_cobrar

4. Compilar:
```bash
python manage.py compilemessages
```

**Verificacion:**
```bash
python -c "
import subprocess
result = subprocess.run(['msgfmt', '--statistics', 'locale/es/LC_MESSAGES/django.po'], capture_output=True, text=True)
print(result.stderr)  # Muestra N translated, M untranslated
"
# Objetivo: >= 280 translated
```

---

### S3-D — SSO: Verificar y completar flow end-to-end

**Problema:** El modelo `SSOProvider` y las vistas `sso_login` / `sso_callback` existen
en `core/sso/` pero el flow completo no ha sido auditado. Hay riesgos de seguridad
potenciales en el callback OIDC/SAML.

**Checklist de auditoria (leer core/sso/views.py completo):**

| Verificacion | Criterio de exito |
|---|---|
| Validacion de parametro `state` | El callback verifica que `state` coincide con el guardado en sesion (anti-CSRF OIDC) |
| Manejo de `error=access_denied` | El IdP puede retornar este parametro; debe redirigir a login con mensaje de error |
| Race condition en `auto_provision` | Usar `get_or_create` atomico, no `filter().exists()` + `create()` |
| `auto_provision=False` falla cerrado | No debe crear usuarios ni hacer login silencioso |
| Validacion de email del token OIDC | El email del JWT debe verificarse antes de provisionar usuario |

**Si se detectan vulnerabilidades durante la auditoria:** Elevar a P0 y crear tickets
prioritarios antes de continuar con S3-A, S3-B y S3-C.

**Tests a escribir:**
```python
# tests/test_sso_security.py
class TestSSOCallback:
    def test_invalid_state_rejected(self): ...
    def test_idp_error_handled_gracefully(self): ...
    def test_auto_provision_false_blocks_new_users(self): ...
    def test_inactive_provider_blocked(self): ...
```

**Verificacion:** `python -m pytest tests/test_sso_security.py -v` — 4/4 passing.

---

## Orden de ejecucion recomendado

```
Semana actual (2-4h):
  S1-A: Doble locale patch → RIESGO: comportamiento erratico en workers
  S1-B: celery.py import settings → RIESGO: CI inestable esporadicamente

Proxima semana (3-5h):
  S2-B: sys.argv en AgenciaManager → IMPACTO: performance en cada query (alta frecuencia)
  S2-A: GDS month map 5 archivos → IMPACTO: mantenibilidad y riesgo de divergencia

Proximo mes (8-16h):
  S3-D: SSO flow verification → PRIMERO (puede elevar prioridad a P0)
  S3-B: CSP unsafe-eval → alta impacto seguridad, requiere testing cuidadoso (3 fases)
  S3-A: PWA service worker → feature completeness
  S3-C: i18n espanol → UX para usuarios venezolanos
```

---

## Metricas de exito por sprint

| Sprint | Metrica objetivo | Comando de verificacion |
|---|---|---|
| Sprint 1 | Tests CI pasan 100% sin AppRegistryNotReady | `python -m pytest --tb=short 2>&1 \| grep -c AppRegistryNotReady` == 0 |
| Sprint 1 | Sin logs de doble locale patch | Buscar "ya parchado" en logs de startup |
| Sprint 2 | Sin usos inline de sys.argv en AgenciaManager | `grep -n "sys.argv" core/models/base.py \| wc -l` <= 5 |
| Sprint 2 | Sin definiciones inline del mapa de meses GDS | `grep -rn "meses_gds\s*={" apps/ \| wc -l` == 0 |
| Sprint 3 | Lighthouse PWA score >= 80 | DevTools Lighthouse tab |
| Sprint 3 | CSP sin unsafe-eval en admin | `curl -I .../admin/ \| grep unsafe-eval` == vacio |
| Sprint 3 | SSO tests 4/4 | `pytest tests/test_sso_security.py -v` |
| Sprint 3 | django.po >= 280 entradas traducidas | `msgfmt --statistics locale/es/LC_MESSAGES/django.po` |

---

## Riesgos residuales post-remediacion

| Riesgo | Nivel | Mitigacion recomendada |
|---|---|---|
| PgBouncer activado en produccion sin USE_PGBOUNCER=true | ALTO | Agregar check en startup: si detecta PgBouncer en DATABASE_URL y CONN_MAX_AGE > 0, loguear ERROR critico al arrancar |
| APIKey dead code importada en 5 archivos | MEDIO | Migrar las 5 importaciones a CronApiKey; agregar test que valide que APIKey no se puede instanciar en produccion |
| scratch_scripts/ en git sin .gitignore | BAJO | Verificar que scratch_scripts/ esta en .gitignore. Si no, agregar entrada |
| Doble autodiscover_tasks en celery.py | BAJO | Consolidar en `app.autodiscover_tasks(packages=["apps", "apps.finance"])` |
| SSO sin tests automatizados | MEDIO-ALTO (si S3-D encuentra vulnerabilidades) | Ejecutar S3-D primero; result determina prioridad final |
