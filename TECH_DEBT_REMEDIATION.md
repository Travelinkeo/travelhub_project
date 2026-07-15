# TECH_DEBT_REMEDIATION.md — TravelHub: Deudas Técnicas y Plan de Remediación
> **PROPÓSITO:** Guía ejecutable para cualquier IA. Cada ítem tiene causa raíz, impacto real, archivos y código de corrección.
> **Generado:** Julio 2025 — Inspección directa del código fuente.
> **Prioridades:** P0=Crítico/Seguridad 🔴 | P1=Alto/Estabilidad 🟠 | P2=Medio/Calidad 🟡 | P3=Bajo/UX 🟢 | P4=Deuda arquitectural 🔵

---

## RESUMEN EJECUTIVO

| Categoría | Ítems Encontrados | Criticidad Máxima |
|---|---|---|
| 🔴 Seguridad | 6 | P0 |
| 🟠 Estabilidad / Producción | 7 | P1 |
| 🟡 Deuda Técnica / Código | 9 | P2 |
| 🟢 UX / Operacional | 4 | P3 |
| 🔵 Arquitectura / Escalabilidad | 5 | P4 |
| **Total** | **31** | — |

---

## FASE P0 — CRÍTICO: SEGURIDAD 🔴
> Ejecutar PRIMERO. Cada ítem aquí puede resultar en pérdida de datos de clientes o bypass de seguridad.

---

### P0-001 — Clave API Gemini expuesta en reglas de memoria global

**Causa raíz:** Las user rules del workspace (RULE[user_global]) contienen literalmente `AIzaSyAnQCcq0Hm6QUcdV8KCwtLG5QvvrNvrKyo` y `AIzaSyBfLgXq2I8ta3kEwXrA6stu7TXWkFkX4Ig` (Google Cloud). Ambas claves son texto plano.

**Impacto:** Cualquier proceso que lea las user rules tiene acceso a estas claves. Las claves de Google pueden incurrir en costos no autorizados de millones de tokens.

**Acción inmediata:**
```bash
# 1. Revocar AMBAS claves desde Google Cloud Console
# Navegar a: console.cloud.google.com → APIs & Services → Credentials → DELETE

# 2. Verificar que .env no está commiteado
git log --all --full-history -- .env
git log --all --full-history -- .env.local

# 3. Si están en historial git, reescribir el historial:
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env .env.local" \
  --prune-empty --tag-name-filter cat -- --all

# 4. Generar nuevas claves y actualizar .env.local únicamente
```

**Verificación:** `gitleaks detect --source . --verbose`

---

### P0-002 — BoletoRetryParseAPIView: IDOR en re-parseo sin validación de tenant

**Causa raíz:** `boleto_views.py:159`, `BoletoRetryParseAPIView.post()` hace:
```python
boleto = BoletoImportado.objects.select_related("agencia", "proveedor").get(pk=pk)
```
Si el contexto del middleware falla, un usuario de Agencia A podría re-parsear un boleto de Agencia B conociendo su `pk`.

**Impacto:** IDOR (Insecure Direct Object Reference) — OWASP A01. Exposición de datos de otro tenant.

**Archivo:** `apps/bookings/views/boleto_views.py` línea 159

**Corrección:**
```python
# ANTES (vulnerable):
boleto = BoletoImportado.objects.select_related("agencia", "proveedor").get(pk=pk)

# DESPUÉS (seguro):
from core.security import get_agencia_from_request, get_object_tenant_or_404
agencia = get_agencia_from_request(request)  # Lanza 403 si no hay agencia
boleto = get_object_tenant_or_404(
    BoletoImportado.all_objects.select_related("agencia", "proveedor"),
    agencia, pk=pk
)
```

---

### P0-003 — VentaDoubleInvoiceAPIView: Sin verificación de tenant en Venta

**Causa raíz:** `boleto_views.py:349`:
```python
venta = Venta.objects.get(pk=pk)  # Sin assert explícito de tenant
```

**Archivo:** `apps/bookings/views/boleto_views.py` línea 349

**Corrección:**
```python
from core.security import get_agencia_from_request, get_object_tenant_or_404
agencia = get_agencia_from_request(request)
venta = get_object_tenant_or_404(Venta, agencia, pk=pk)
```

---

### P0-004 — `system_context` sin límite de tiempo → ventana ilimitada de bypass

**Causa raíz:** El context manager `system_context()` deshabilita todos los filtros de tenant sin timeout ni logging de auditoría. Si una tarea Celery levanta una excepción dentro del contexto, el bypass queda activo hasta que el worker muere.

**Impacto:** Fuga de datos cross-tenant en producción.

**Archivo:** `core/middleware.py`

**Corrección:**
```python
@contextmanager
def system_context(reason: str = "unspecified", max_seconds: float = 30):
    """Context manager para acceso global. SIEMPRE proveer reason."""
    logger.warning(f"🔓 system_context ABIERTO — Razón: {reason}")
    token = system_context_var.set(True)
    start = time.monotonic()
    try:
        yield
    finally:
        elapsed = time.monotonic() - start
        system_context_var.reset(token)
        logger.info(f"🔒 system_context CERRADO — {reason} — {elapsed:.2f}s")
        if elapsed > max_seconds:
            logger.error(f"⚠️ system_context excedió {max_seconds}s: {reason}")
```

---

### P0-005 — Webhook Stripe sin verificación de firma verificada en todos los endpoints

**Causa raíz:** No fue posible confirmar que TODOS los endpoints de webhook Stripe validan la firma con `stripe.Webhook.construct_event()`.

**Impacto:** Un atacante puede forjar webhooks Stripe y cambiar el plan de una agencia a ENTERPRISE sin pagar.

**Verificación requerida:**
```bash
grep -rn "construct_event\|webhook" apps/ core/ --include="*.py" | grep -i stripe
```

**Patrón correcto obligatorio:**
```python
@csrf_exempt
@api_view(["POST"])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.warning(f"Stripe webhook inválido: {e}")
        return Response({"error": "Invalid signature"}, status=400)
```

---

### P0-006 — `BoletoUploadAPIView` expone traceback completo en respuestas 500

**Causa raíz:** `boleto_views.py:126-129`:
```python
return Response({"error": f"Fallo al recibir el archivo: {str(e)}"}, ...)
```
`str(e)` puede incluir rutas de archivo, nombres de tablas SQL, stack traces con paths internos.

**Impacto:** Information Disclosure — OWASP A09.

**Corrección:**
```python
import uuid
except Exception as e:
    error_id = uuid.uuid4().hex[:8]
    logger.exception(f"[{error_id}] Error al procesar subida de boleto")
    return Response(
        {"error": f"Error interno. Referencia: {error_id}"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
```
**Aplica a:** Todos los `except Exception as e: return Response({"error": str(e)}, ...)` en `boleto_views.py`.

---

## FASE P1 — ALTO: ESTABILIDAD Y PRODUCCIÓN 🟠

---

### P1-001 — Doble signal `post_save` en `BoletoImportado` → doble ejecución de parseo

**Causa raíz:** `core/signals.py` tiene DOS receivers para `post_save` de `BoletoImportado` (líneas 33 y 56). Ambos se ejecutan en cada `save()`, pudiendo causar procesamiento duplicado.

**Impacto:** Double billing de Gemini API, PDFs generados dos veces, race conditions en `estado_parseo`.

**Verificación:**
```bash
grep -n "post_parse_automation\|trigger_parsing" apps/bookings/services/boleto_service.py
```

**Corrección (si hay duplicado):**
```python
# Consolidar en un único signal:
@receiver(post_save, sender="bookings.BoletoImportado")
def on_boleto_saved(sender, instance, created, **kwargs):
    if are_signals_blocked():
        return
    if getattr(instance, "_skip_auto_parse", False):
        return
    update_fields = kwargs.get("update_fields") or set()
    _INTERNAL_FIELDS = {"venta_asociada","estado_parseo","log_parseo","archivo_pdf_generado"}
    if update_fields and update_fields.issubset(_INTERNAL_FIELDS):
        return
    _on_commit(_trigger_parsing, instance.pk)
```

---

### P1-002 — `celery.py` llama `django.setup()` explícitamente → crash en tests

**Causa raíz:** `travelhub/celery.py` tiene una llamada explícita `django.setup()` que no es idempotente cuando pytest-django ya lo configuró.

**Corrección:**
```python
# celery.py — Patrón seguro estándar:
import os
from celery import Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings.development")
app = Celery("travelhub")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
# ← ELIMINAR django.setup() explícito
```

---

### P1-003 — `CONN_MAX_AGE=600` incompatible con `ATOMIC_REQUESTS=True` bajo PgBouncer

**Causa raíz:** Con PgBouncer activo en modo transaction, `CONN_MAX_AGE > 0` rompe el RLS porque las variables `SET LOCAL app.current_agencia_id` escapan de la transacción al devolver la conexión al pool.

**Impacto:** 🚨 **FUGA DE DATOS CROSS-TENANT EN PRODUCCIÓN** si se usa PgBouncer.

**Corrección:**
```python
# settings/production.py — Añadir:
import os
if os.getenv("USE_PGBOUNCER", "false").lower() == "true":
    DATABASES["default"]["CONN_MAX_AGE"] = 0
```
```bash
# .env.production:
USE_PGBOUNCER=true
```

---

### P1-004 — Cache de agencia TTL=120s permite acceso 2min después de desactivar agencia

**Causa raíz:** `core/security.py` línea 34: `_USER_AGENCIA_CACHE_TIMEOUT = 120`.

**Impacto:** Si se desactiva una agencia por compromiso de seguridad, los usuarios siguen accediendo por hasta 2 minutos.

**Corrección:**
```python
# security.py:
_USER_AGENCIA_CACHE_TIMEOUT = 30  # Reducir a 30 segundos

# Añadir signal de invalidación inmediata:
@receiver(post_save, sender=Agencia)
def on_agencia_changed(sender, instance, **kwargs):
    if not instance.activa:
        from core.security import invalidate_all_agency_caches
        invalidate_all_agency_caches(instance.pk)
```

---

### P1-005 — `locale.setlocale` monkey patch global en `ticket_parser_service.py`

**Causa raíz:** El patch se aplica en tiempo de importación del módulo, afectando globalmente todas las librerías que usen `locale.setlocale`.

**Corrección:** Mover el patch a un context manager y aplicarlo solo durante el parseo:
```python
@contextmanager
def _safe_locale_context():
    original = locale.setlocale
    locale.setlocale = _make_safe_setlocale(original)
    try:
        yield
    finally:
        locale.setlocale = original

def parse_ticket_file(boleto):
    with _safe_locale_context():
        # ... lógica de parseo
```

---

### P1-006 — `UniversalAIParser` trunca texto a 15,000 chars silenciosamente

**Causa raíz:** `ai_universal_parser.py`: `text_limpio = text_limpio[:15000]` sin log ni flag en resultado.

**Impacto:** Parseo incorrecto de boletos grandes sin que el usuario lo sepa.

**Corrección:**
```python
WAS_TRUNCATED = False
if len(text_limpio) > 15000:
    WAS_TRUNCATED = True
    logger.warning(f"⚠️ Texto truncado de {len(text_limpio)} a 15,000 chars.")
    text_limpio = text_limpio[:15000]
# Incluir en resultado: final_result["_text_was_truncated"] = WAS_TRUNCATED
```

---

### P1-007 — Señales de `Factura` disparan WhatsApp dentro de `on_commit` con fallback síncrono

**Causa raíz:** `_send_factura_whatsapp` en `signals.py` puede ejecutar `task.apply()` síncronamente si el broker está caído. Si esa tarea hace operaciones DB, puede causar datos inconsistentes dentro de una transacción.

**Verificación:**
```bash
grep -n "safe_delay\|\.apply(" apps/finance/services/factura_service.py
```

**Corrección:** Las tareas disparadas desde `on_commit` NO deben tener fallback síncrono con operaciones DB críticas. Usar siempre `task.delay()` con reintentos exponenciales.

---

## FASE P2 — MEDIO: DEUDA TÉCNICA Y CALIDAD DE CÓDIGO 🟡

---

### P2-001 — Comentario placeholder en `ParsedTicketData.to_dict()`

**Causa raíz:** `base_parser.py` líneas 74-76 contienen un comentario `[OMITIDO PARA BREVEDAD, ...]` que es documentación falsa.

**Corrección:** Eliminar el comentario y reemplazar con documentación real.

---

### P2-002 — 15+ archivos de debug en la raíz del proyecto

**Archivos:** `debug_celery_tasks.py`, `debug_copa.py`, `debug_in_docker.py`, `debug_ticket.py`, `test_copa*.py`, `_fix_imports*.py`

**Acción:**
```bash
grep -rn "api_key\|password\|secret" debug_*.py _fix_imports*.py test_copa*.py
mkdir -p scratch_scripts
mv debug_*.py _fix_imports*.py test_copa*.py scratch_scripts/
echo "scratch_scripts/" >> .gitignore
```

---

### P2-003 — `requirements/base.txt` incluye `amadeus` y `flights` SDK sin uso verificado

**Verificación:**
```bash
grep -rn "from amadeus\|import amadeus\|from flights\|import flights" apps/ core/ --include="*.py"
```
Si no hay usos, eliminar de `requirements/base.txt`.

---

### P2-004 — `celery.py` usa `settings.production` como default en desarrollo

**Causa raíz:** `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings.production")` — workers locales arrancan con config de producción si no se define la variable.

**Corrección:**
```python
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "travelhub.settings.development")
```

---

### P2-005 — Mapa de meses GDS definido 4 veces en el código

**Causa raíz:** `{1:"ENE", 2:"FEB", ...12:"DIC"}` está duplicado en `normalization.py` y 3 veces en `ai_schemas.py`.

**Corrección:**
```python
# Crear: apps/automation/parsers/parsing_utils.py
GDS_MONTHS = {1:"ENE",2:"FEB",3:"MAR",4:"ABR",5:"MAY",6:"JUN",
              7:"JUL",8:"AGO",9:"SEP",10:"OCT",11:"NOV",12:"DIC"}
# Importar desde todos los puntos de uso.
```

---

### P2-006 — `AgenciaManager.get_queryset()` tiene `import sys` y parsing de `sys.argv` en cada query

**Causa raíz:** Código ejecutado en cada acceso a la BD que hace parsing de `sys.argv`.

**Corrección:**
```python
# Mover a nivel de módulo (una sola vez al iniciar):
import sys
_IS_MANAGEMENT_COMMAND = (
    "manage.py" in (sys.argv[0] if sys.argv else "") and
    any(arg in sys.argv for arg in ["makemigrations","migrate","shell","check","test"])
)
_IS_PYTEST = "pytest" in sys.modules
```

---

### P2-007 — `BoletoImportado.id` tiene `@property` que puede romper el ORM

**Causa raíz:** `importacion.py` define un `@property id` que sobreescribe el `id` automático de Django.

**Verificación:**
```bash
python manage.py shell -c "
from apps.bookings.models import BoletoImportado
print(BoletoImportado.objects.filter(id=1).query)
"
Si la query es correcta, el property es inocuo. Si falla, eliminar y usar `pk` o `id_boleto_importado` explícitamente.

---

### P2-008 — Tests en raíz no integrados en pytest.ini

**Causa raíz:** `pytest.ini` define `testpaths = tests/` pero hay `test_copa*.py` en la raíz.

**Acción:**
```bash
python -m pytest --collect-only -q 2>&1 | grep "test_copa"
# Si NO aparecen: mover a scratch_scripts/ (ya cubierto en P2-002)
```

---

### P2-009 — `_build_redis_url()` definida en `settings/base.py` (lógica de negocio en settings)

**Corrección:** Mover a `core/utils/redis_utils.py` e importar desde settings.

---

### P2-010 — Archivos de Señales Huérfanos/Obsoletos en el Core

**Causa raíz:** `core/signals_contabilidad.py` solo contiene una función helper no utilizada por ningún dispatcher de señal (el modelo asociado fue eliminado en refactorizaciones previas). `core/signals_rls.py` está totalmente vacío (0 bytes).

**Impacto:** Ruido y confusión de mantenimiento para desarrolladores e IAs.

**Corrección:** Eliminar físicamente `core/signals_contabilidad.py` y `core/signals_rls.py` del repositorio.

---

### P2-011 — Bloque de transacción atómica anidado dentro de `Venta.save()`

**Causa raíz:** `apps/bookings/models/venta.py` hace `with transaction.atomic():` dentro de un bucle `for` en el método `.save()` para autoincrementar el localizador de forma diaria, pero no utiliza `select_for_update()`, permitiendo duplicados ya que el campo localizador no tiene índice único.

**Impacto:** Riesgo de bloqueos y fallos de Savepoints anidados si se llama a `.save()` dentro de transacciones ya abiertas por la capa de servicio (Service Layer) o middlewares.

**Corrección:** Delegar la generación única del localizador de la venta a un servicio orquestador (p. ej., `VentaAutomationService`) usando una consulta `select_for_update()` sobre un modelo de numeración dedicado y atómico, eliminando la transacción interna en el `.save()`.

---

### P1-008 — Cifrado Fernet sin clave válida configurada por defecto en testing (REMEDIADO)

**Causa raíz:** Al ejecutar la suite de pruebas locales sin `.env.local` configurado con una clave base64 válida, los modelos con campos encriptados (`EncryptedCharField` como los de Pasajero/Cliente) lanzaban `OperationalError: Fernet key must be 32 url-safe base64-encoded bytes` al intentar guardar.

**Corrección:** Se configuró una clave estática Fernet válida `ENCRYPTION_KEY` por defecto al final de `travelhub/settings/testing.py`.

---

### P1-009 — Tests unitarios congelados por peticiones de red WeasyPrint síncronas (REMEDIADO)

**Causa raíz:** En entornos sin workers de Celery/Redis (como la suite de tests locales), el pipeline de parseo invoca WeasyPrint de forma síncrona, lo que hace llamadas de red para descargar Google Fonts y hojas de estilo externas, causando bloqueos por timeout si no hay acceso a internet.

**Corrección:** Se decoró globalmente la clase `TestHybridParser` en `tests/test_hybrid_parser.py` con `@patch("apps.automation.services.ticket_parser_service._generate_pdf_sync")` para mockear la generación física de PDFs durante los tests de extracción de texto.

---

## FASE P3 — BAJO: UX Y OPERACIONAL 🟢

---

### P3-001 — Boletos en estado `QUE` (Cola Llena) nunca se reintentarán automáticamente

**Corrección:** Añadir a `celery_beat_schedule.py`:
```python
"retry-queued-boletos-every-10-minutes": {
    "task": "apps.bookings.tasks.retry_queued_boletos_task",
    "schedule": 600.0,
},
```
Y crear la tarea `retry_queued_boletos_task()` que procese máximo 50 boletos en estado `QUE`.

---

### P3-002 — No existe endpoint de polling para conocer el estado de parseo

**Corrección:** Añadir `GET /api/boletos/{id}/status/` → `BoletoStatusAPIView`:
```python
class BoletoStatusAPIView(InternalAPIAuthMixin, APIView):
    def get(self, request, pk):
        agencia = get_agencia_from_request(request)
        boleto = get_object_tenant_or_404(BoletoImportado.all_objects, agencia, pk=pk)
        return Response({
            "estado_parseo": boleto.estado_parseo,
            "pdf_url": boleto.get_pdf_url() if boleto.estado_parseo == "COM" else None,
            "log_parseo": (boleto.log_parseo or "")[-500:],
        })
```

---

### P3-003 — No hay alertas cuando una agencia consume >X% de cuota Gemini global

**Corrección:** Añadir task diario de reporte de uso de IA por agencia a `celery_beat_schedule.py`.

---

### P3-004 — `BoletoImportado.log_parseo` crece ilimitadamente con re-parseos

**Corrección:**
```python
MAX_LOG_LENGTH = 4000
existing_log = str(boleto.log_parseo or "")
new_entry = f"[{datetime.now().isoformat()}] {new_log_entry}"
combined = f"{existing_log}\n{new_entry}"
boleto.log_parseo = combined[-MAX_LOG_LENGTH:]
```

---

## FASE P4 — ARQUITECTURAL: ESCALABILIDAD Y DEUDA ESTRUCTURAL 🔵

---

### P4-001 — El parser híbrido (AI + Regex) no tiene métricas de precisión

**Plan:** Añadir campos `parser_used` y `confidence_score` a `BoletoImportado`. Crear reporte semanal de métricas.

---

### P4-002 — `travelhub/urls.py` tiene rutas mezcladas (God Object de URLs)

**Plan:** Extraer a `urls_infrastructure.py`, `urls_auth.py`, `urls_public.py`.

---

### P4-003 — `datos_parseados` JSONField sin schema versionado

**Plan:** Añadir `datos_parseados_version = CharField` y management command `migrate_parsed_data`.

---

### P4-004 — 3 canales de notificaciones (WA/Telegram/Email) sin abstracción unificada

**Plan:** Crear `apps/communications/services/notification_router.py` con `NotificationRouter.send(agencia, event_type, payload)`.

---

### P4-005 — Documentación arquitectural (`CONTEXT_MAP.md`) puede quedar desactualizada

**Plan:** Añadir check de CI/CD que alerte si archivos críticos se modifican sin actualizar `CONTEXT_MAP.md`.

---

## ORDEN DE EJECUCIÓN RECOMENDADO

```
Semana 1 (Urgente):
  P0-001 → Revocar claves expuestas (requiere Google Console)
  P0-006 → Eliminar tracebacks en respuestas 500
  P0-002 → Fix IDOR en BoletoRetryParseAPIView
  P0-003 → Fix IDOR en VentaDoubleInvoiceAPIView

Semana 2 (Seguridad):
  P0-004 → Timeout + logging a system_context()
  P0-005 → Verificar y hardening webhooks Stripe
  P1-004 → Reducir TTL cache agencia + signal de invalidación

Semana 3 (Estabilidad):
  P1-001 → Consolidar double signal BoletoImportado
  P1-002 → Fix django.setup() en celery.py
  P1-003 → CONN_MAX_AGE=0 con USE_PGBOUNCER=true
  P1-005 → Locale monkey patch a contextmanager
  P1-008 → [REMEDIADO] Clave Fernet estática en testing
  P1-009 → [REMEDIADO] Mocking síncrono de WeasyPrint en tests

Semana 4 (Calidad):
  P2-001 → Limpiar comentario placeholder en to_dict()
  P2-002 → Mover archivos debug a scratch_scripts/
  P2-004 → Fix default settings module en celery.py
  P2-005 → Centralizar GDS_MONTHS
  P2-007 → Evaluar property id en BoletoImportado
  P2-010 → Eliminar signals_contabilidad.py y signals_rls.py
  P2-011 → Extraer transacciones internas de Venta.save()

Semana 5 (Operacional):
  P3-001 → Tarea retry boletos QUE
  P3-002 → Endpoint GET /api/boletos/{id}/status/
  P3-004 → Truncar log_parseo a 4000 chars

Mes 2 (Arquitectural):
  P4-001 → Métricas de precisión del parser
  P4-002 → Refactoring de urls.py
  P4-003 → Versionado datos_parseados JSONField
  P4-004 → NotificationRouter unificado
  P4-005 → CI/CD check documentación
```

---

## COMANDOS DE VERIFICACIÓN RÁPIDA

```bash
# Verificar no hay claves en git:
gitleaks detect --source . --verbose

# Correr tests:
python -m pytest tests/ -x -q --tb=short

# Verificar imports críticos:
python -c "from apps.automation.parsers.base_parser import ParsedTicketData; print('OK')"
python -c "from core.middleware import ThreadLocalContextMiddleware; print('OK')"
python -c "from apps.automation.services.ai_engine import ai_engine; print('OK')"

# Buscar credenciales en archivos debug:
grep -rn "api_key\|password\|secret" debug_*.py 2>/dev/null

# Cobertura de tests:
python -m pytest tests/ --cov=apps --cov=core --cov-report=term-missing -q 2>&1 | tail -20
```

---

*Generado por análisis estático del código fuente TravelHub. Para regenerar: leer `CONTEXT_MAP.md` y ejecutar inspección de los archivos listados.*
