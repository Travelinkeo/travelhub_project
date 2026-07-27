# TECH_DEBT_REMEDIATION.md — TravelHub: Deudas Técnicas y Plan de Remediación
> **PROPÓSITO:** Guía ejecutable para cualquier IA. Cada ítem tiene causa raíz, impacto real, archivos y código de corrección.
> **Generado:** Julio 2025 — Inspección directa del código fuente.
> **Última actualización:** 2026-07-26 (commit `d35a1bfc`)
> **Prioridades:** P0=Crítico/Seguridad 🔴 | P1=Alto/Estabilidad 🟠 | P2=Medio/Calidad 🟡 | P3=Bajo/UX 🟢 | P4=Deuda arquitectural 🔵

---

## RESUMEN EJECUTIVO

| Categoría | Total | Resueltos | Pendientes |
|---|---|---|---|
| 🔴 P0 — Seguridad | 6 | 6 | 0 |
| 🟠 P1 — Estabilidad | 9 | 9 | 0 |
| 🟡 P2 — Calidad | 11 | 10 | 1 |
| 🟢 P3 — UX/Operacional | 4 | 1 | 3 |
| 🔵 P4 — Arquitectura | 5 | 0 | 5 |
| **Total** | **35** | **26** | **9** |

---

## ✔️ RESUELTOS (26 items)

### 🔴 P0 — Seguridad

| ID | Descripción | Resolución |
|----|------------|------------|
| P0-001 | Claves Gemini en user rules | `git filter-repo` eliminó `.amazonq/` del historial. Claves revocadas en Google Cloud Console. |
| P0-002 | IDOR BoletoRetryParseAPIView | `get_object_tenant_or_404()` en boleto_views.py:165-168 |
| P0-003 | IDOR VentaDoubleInvoiceAPIView | `get_object_tenant_or_404(Venta, agencia, pk=pk)` en boleto_views.py:365-368 |
| P0-004 | system_context sin timeout | `max_seconds=60.0` con logging + alerta en middleware.py:69 |
| P0-005 | Webhook Stripe sin firma | `stripe.Webhook.construct_event()` validado en views_webhooks.py:159 |
| P0-006 | Traceback en 500 | Todos los `str(e)` reemplazados con `error_id` + `logger.exception` en boleto_views.py |

### 🟠 P1 — Estabilidad

| ID | Descripción | Resolución |
|----|------------|------------|
| P1-001 | Doble signal BoletoImportado | Verificado: existe un único `@receiver(post_save)` en core/signals.py |
| P1-002 | django.setup() en celery.py | No existe llamada a `django.setup()` en celery.py |
| P1-003 | CONN_MAX_AGE vs PgBouncer | `USE_PGBOUNCER` env var en base.py:225 condiciona CONN_MAX_AGE=0 |
| P1-004 | Cache TTL=120s | Reducido a 30s + signal de invalidación en security.py |
| P1-005 | locale.setlocale global | Movido a `core/locale_patch.py` con `safe_setlocale` wrapper (defensivo) |
| P1-006 | Truncación silenciosa 15k chars | Log + flag `_text_was_truncated` en ai_universal_parser.py |
| P1-007 | WhatsApp síncrono en signals | Verificado: usa `.delay()`, no `.apply()` |
| P1-008 | Fernet sin clave en testing | Clave estática en testing.py |
| P1-009 | WeasyPrint bloquea tests | Mockeado con `@patch` en tests |

### 🟡 P2 — Calidad

| ID | Descripción | Resolución |
|----|------------|------------|
| P2-001 | Comentario placeholder to_dict() | No existe en código actual |
| P2-002 | Debug files en raíz | Eliminados del repositorio |
| P2-003 | flights/amadeus SDK sin uso | `flights==0.9.0` eliminado de requirements/base.txt |
| P2-004 | celery.py default production | Cambiado a `travelhub.settings.development` |
| P2-005 | GDS months duplicado | Centralizado en `parsing_utils.py` via normalization.py |
| P2-006 | sys.argv en cada query | Constantes `_IS_PYTEST`/`_IS_MANAGEMENT_COMMAND` en security.py y base.py |
| P2-007 | @property id en BoletoImportado | Eliminado; comentario ⚠️ advierte no usar filter(id=...) |
| P2-008 | Tests en raíz | Movidos a scratch_scripts/ |
| P2-010 | Señales huérfanas | Archivos `signals_contabilidad.py` y `signals_rls.py` no existen |
| P2-011 | Nested atomic en Venta.save() | Usa `SecuenciaVentaDiaria` con `select_for_update()` |

---

## 📋 PENDIENTES (9 items)

---

### 🟡 P2-009 — `_build_redis_url()` en settings/base.py

**Causa raíz:** Función definida dentro de settings/base.py (lógica de negocio en settings).

**Corrección aplicada:** Movida a `core/utils/redis_utils.py` como `build_redis_url()` e importada desde settings.

**Estado:** ✅ RESUELTO (commit `d35a1bfc`)

---

### 🟢 P3-001 — Boletos QUE nunca reintentados

**Causa raíz:** No existía tarea programada para boletos en estado `COLA_LLENA`.

**Estado:** ✅ RESUELTO — `retry_queued_boletos_task()` existe en `apps/bookings/tasks.py:691`.

---

### 🟢 P3-002 — No existe endpoint de polling de estado de parseo

**Causa raíz:** No hay `GET /api/boletos/{id}/status/` para consultar estado de parseo asíncrono.

**Corrección:**
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

**Archivo:** `apps/bookings/views/boleto_views.py`
**Estado:** PENDIENTE

---

### 🟢 P3-003 — No hay alertas de cuota Gemini

**Causa raíz:** No existe tarea diaria que alerte cuando una agencia consume >X% de cuota Gemini global.

**Corrección:** Añadir task diario de reporte de uso de IA por agencia a `celery_beat_schedule.py`.

**Estado:** PENDIENTE

---

### 🟢 P3-004 — `log_parseo` crece ilimitadamente

**Causa raíz:** `BoletoImportado.log_parseo` es un TextField sin límite, y en cada re-parseo se concatena.

**Corrección aplicada:** `save()` override en `importacion.py` trunca a `MAX_LOG_LENGTH = 4000` chars.

**Estado:** ✅ RESUELTO (commit `d35a1bfc`)

---

### 🔵 P4-001 — Métricas de precisión del parser

**Plan:** Añadir campos `parser_used` y `confidence_score` a `BoletoImportado`. Crear reporte semanal de métricas.

**Estado:** PENDIENTE

---

### 🔵 P4-002 — `travelhub/urls.py` es God Object

**Plan:** Extraer a `urls_infrastructure.py`, `urls_auth.py`, `urls_public.py`.

**Estado:** PENDIENTE

---

### 🔵 P4-003 — `datos_parseados` JSONField sin schema versionado

**Plan:** Añadir `datos_parseados_version = CharField` y management command `migrate_parsed_data`.

**Estado:** PENDIENTE

---

### 🔵 P4-004 — 3 canales de notificación sin abstracción unificada

**Plan:** Crear `apps/communications/services/notification_router.py` con `NotificationRouter.send(agencia, event_type, payload)`.

**Estado:** PENDIENTE

---

### 🔵 P4-005 — Documentación arquitectural desactualizable

**Plan:** Añadir check de CI/CD que alerte si archivos críticos se modifican sin actualizar `CONTEXT_MAP.md`.

**Estado:** PENDIENTE

---

## ORDEN DE EJECUCIÓN RECOMENDADO

```
Inmediato (si no se hizo aún):
  P0-001 → Confirmar claves Gemini revocadas en Google Cloud Console
  P0-006 → Confirmar ningún str(e) en respuestas 500 de vistas de usuario

Próximo:
  P3-002 → Endpoint GET /api/boletos/{id}/status/
  P3-003 → Alerta diaria de cuota Gemini por agencia

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
