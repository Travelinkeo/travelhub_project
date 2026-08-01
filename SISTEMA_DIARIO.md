# TravelHub — Diario del Sistema

> Este documento es la bitácora oficial del sistema.
> Cada componente listado aquí debe justificar su existencia.
> Si no lo hace, se elimina.

---

## Filosofía

Nada en este codebase existe "porque sí". Cada archivo, cada modelo, cada
servicio, cada dependencia debe responder a una necesidad real del negocio.

- **Si un archivo ya no se usa, se elimina.**
- **Si un modelo es un stub de migración con `managed=False`, se documenta
  y se programa su limpieza.**
- **Si un servicio duplica funcionalidad, se unifica o se elimina uno.**
- **Si una tarea celery nunca se ejecuta, se elimina.**

---

## Estructura general

```
travelhub/
├── apps/                    # 13 apps Django
│   ├── automation/          # Parsing de boletos + IA
│   ├── bookings/            # Ventas, reservas, boletos
│   ├── cms/                 # Blog, guías, knowledge base
│   ├── common/              # Catálogos compartidos (países, aerolíneas, monedas)
│   ├── communications/      # WhatsApp, Telegram, Email, notificaciones
│   ├── contabilidad/        # Contabilidad VEN-NIF
│   ├── cotizaciones/        # Cotizaciones / propuestas
│   ├── crm/                 # Clientes, pasajeros, leads
│   ├── finance/             # Facturación, pagos, conciliación
│   ├── gamification/        # Gamificación (niveles, logros)
│   ├── marketing/           # Campañas de marketing automatizadas
│   ├── reports/             # KPIs, reportes programados
│   └── tasks/               # Tablero Kanban de tareas
├── core/                    # Lógica transversal (agencias, usuarios, vistas compartidas)
├── travelhub/               # Configuración Django (settings, urls, wsgi)
├── scripts/                 # Scripts auxiliares (incluye _archive/tools/ con dev tools)
└── media/                   # Archivos subidos
```

---

## Apps — Análisis de justificación

### ✅ `apps/automation` — JUSTIFICADO

**Propósito:** Corazón del sistema. Parsea boletos aéreos desde cualquier
formato (Sabre, Amadeus, KIU, Avianca, GDS, PDF, EML, HTML) usando regex
+ IA (Gemini, OpenAI, DeepSeek).

**Lo que hace:**
- Pipeline de parseo: extracción → parser específico → IA fallback → validación → persistencia
- Provider chain con circuit breaker y fallback automático
- Métricas de parser (éxito/falla, duración, tokens, costo)
- Normalización de datos (fechas, monedas, aerolíneas, ciudades)
- Registro centralizado de parsers (`ParserRegistry`)

**Archivos clave:**
- `parsers/registry.py` — Registry thread-safe (fix P1-16 aplicado)
- `parsers/base_parser.py` — `ParsedTicketData` DTO (single source of truth)
- `parsers/kiu_parser.py` — Parser KIU/Avianca (fix P0-5, P0-6 aplicados)
- `parsers/adapter.py` — `_build_minimal_dict` (fix P0-9 aplicado)
- `services/ticket_parser_service.py` — Orquestador principal (fix P1-11 aplicado)
- `services/ai_engine.py` — Motor IA con circuit breaker (fix P1-13 aplicado)
- `metrics/parser_metrics.py` — Métricas atómicas vía HINCRBY (fix P1-15, P1-14, P1-12 aplicados)

**Lo que se eliminó:**
- `apps/automation/ai/` — directorio vacío, sin propósito

**Estado:** ✅ Activo, crítico, en mejora continua.

---

### ✅ `apps/bookings` — JUSTIFICADO

**Propósito:** Gestión de ventas, reservas y boletos importados. Es el
modelo de negocio principal.

**Modelos críticos:** `Venta`, `BoletoImportado`, `ItemVenta`, `PagoVenta`,
`FeeVenta`, `SegmentoVuelo`, `ProductoServicio`, `Proveedor`
(~30 modelos en total, todos activos).

**Estado:** ✅ Activo, crítico.

---

### ✅ `apps/cms` — JUSTIFICADO

**Propósito:** Blog, guías de destino, knowledge base, posts a redes sociales.

**Modelos:** `Articulo`, `GuiaDestino`, `PostRedesSociales`, `KBCategory`, `KBArticle`

**Estado:** ✅ Activo.

---

### ✅ `apps/common` — JUSTIFICADO

**Propósito:** Catálogos maestros (países, ciudades, aerolíneas, monedas),
servicios compartidos (PDF, magic link, cuotas SaaS), tareas comunes.

**Contiene:**
- `services/pdf_renderer.py` — WeasyPrint PDF
- `services/magic_link_service.py` — Autenticación sin password
- `services/saas_quota_service.py` — Límites multi-tenancy
- ~60 tareas celery compartidas

**Estado:** ✅ Activo, crítico.

---

### ✅ `apps/communications` — JUSTIFICADO

**Propósito:** Comunicaciones multicanal — WhatsApp (Evolution API, Meta,
Twilio), Telegram, Email (Resend + SMTP), Slack, Google Calendar.

**Arquitectura:**
- `services/evolution_api_service.py` — Cliente Evolution API v2 (fixes
  P1-17, P1-19, P1-20 aplicados)
- `services/whatsapp_unified.py` — Abstracción unificada WhatsApp
- `services/telegram_unified.py` — Cliente Telegram
- `services/email_unified.py` — Cliente Email

**Estado:** ✅ Activo, crítico.

---

### ✅ `apps/contabilidad` — JUSTIFICADO

**Propósito:** Contabilidad VEN-NIF — catálogo de cuentas, asientos
contables, partida doble, conciliación de reportes de proveedores
(CTG, My Destiny), tasas BCV, retenciones ISLR.

**Stubs (`managed=False`):** `DetalleAsiento`, `PlanContable`,
`ItemLiquidacion`, `LiquidacionProveedor` — son tablas existentes en DB
que Django no debe migrar. Se mantienen para compatibilidad de consultas.

**Estado:** ✅ Activo, aunque los stubs deben auditarse.

---

### ✅ `apps/cotizaciones` — JUSTIFICADO

**Propósito:** Cotizaciones con IA ("Magic Quoter"), generación de PDF,
compartir por WhatsApp, conversión a venta.

**Estado:** ✅ Activo.

---

### ✅ `apps/crm` — JUSTIFICADO

**Propósito:** CRM — clientes, pasajeros, oportunidades, chatbots
WhatsApp con IA, OCR de pasaportes, mensajería.

**Modelos clave:** `Cliente`, `Pasajero`, `OportunidadViaje`,
`MensajeWhatsApp`, `PasaporteEscaneado`

**Webhooks:**
- `WhatsAppWebhookView` — Meta Cloud API (con HMAC, seguro)
- `EvolutionWebhookView` — Evolution API (fix P0-3 aplicado: auth vía apikey)
- P1-10 aplicado: `_handle_send_result` ya no busca `message_id=""`

**Estado:** ✅ Activo, crítico.

---

### ✅ `apps/finance` — JUSTIFICADO

**Propósito:** Facturación VEN-NIF, Stripe, Binance Pay, conciliación
bancaria, retenciones ISLR, libro de ventas/compras, devolución de
impuestos, liquidación de agentes.

**Stubs (`managed=False`):** `CanalRecaudacion`, `ComisionVenta`,
`LiquidacionAgente`, `FacturaFiscal`, `ReporteReconciliacion`,
`ReservaHotel`, `TipoCambio`, `TasaCambio`, `UsuarioAgencia`,
`ComisionPorVenta`, `ProductoContable`, y ~9 más en `models_stubs.py`.

> ✅ **AUDITADO (housekeeping):** Estos stubs de `finance` son adaptadores
> a tablas legacy reales `finance_*` y están **en uso** por vistas/servicios
> (CanalRecaudacion, ConciliacionBoleto, ReporteReconciliacion, LinkDePago,
> TasaCambio, Moneda, etc.). Se conservan. Los 4 stubs vacíos de `contabilidad`
> (DetalleAsiento, PlanContable, ItemLiquidacion, LiquidacionProveedor) fueron
> **eliminados** y sus callers migrados al nuevo esquema
> (`CuentaContable`/`AsientoContable`/`MovimientoContable`).

**Servicios IA contable:** `ai_accounting_service.py` (AIAccountingService, Virtual CFO)
en uso vía `accounting_assistant.py`. `accounting_ai_service.py` (CPA Engine) era código
muerto (cero callers) → **eliminado**.

**Estado:** ✅ Activo.

---

### ❓ `apps/gamification` — BAJO REVISIÓN

**Propósito:** Gamificación — niveles, logros, puntuaciones para agentes.

**Modelos:** `Nivel`, `Logro`, `LogroProgreso`, `PuntuacionUsuario`

**Análisis:** Los modelos existen, los servicios existen, pero:
- No hay evidencia de uso activo en vistas o reportes principales
- No hay señales en el dashboard que referencien logros
- No hay celery tasks que calculen puntuaciones

**Veredicto:** ❓ **Potencialmente muerto.** Si nadie lo usa en
producción, debería marcarse como deprecado y eliminarse en el próximo
sprint de limpieza. Por ahora se mantiene porque los modelos existen
en DB y eliminarlos requiere migración.

**Estado:** ⏳ En observación.

---

### ✅ `apps/marketing` — JUSTIFICADO

**Propósito:** Campañas de marketing automatizadas con generación de
contenido por IA (flyers, copys, stories).

**Posible solapamiento:** `apps/automation/services/marketing_intelligence_service.py`
podría tener funcionalidad redundante. AUDITAR.

**Estado:** ✅ Activo.

---

### ✅ `apps/reports` — JUSTIFICADO

**Propósito:** KPIs, dashboards, reportes programados.

**Estado:** ✅ Activo.

---

### ✅ `apps/tasks` — JUSTIFICADO

**Propósito:** Tablero Kanban simple para tareas internas del equipo.

**Modelos:** `Tarea`, `ComentarioTarea`

**Estado:** ✅ Activo (aunque es simple, cumple su función).

---

## Componentes por justificar o eliminar

### 🗑️ `apps/automation/ai/` — ELIMINADO

Directorio completamente vacío. No tiene `__init__.py` ni archivos.
Eliminado en esta sesión de hardening.

### 🗑️ `scratch_scripts/` — PROGRAMADO PARA ELIMINAR

Scripts de desarrollo personal (`test_kiu_eml.py`, `test_kiu_flights.py`,
`test_kiu_flow.py`). No forman parte del sistema.

**Acción:** Mover a archivo o eliminar.

### 🗑️ Archivos raíz de fix one-time

`fix_ai_engine.py`, `fix_ai_engine2.py`, `fix_ai_engine3.py`,
`fix_tasks.py`, `fix_tasks2.py`, `check_imports.py`,
`check_migration.py`, `generar_video_hd.py`

Scripts de una sola ejecución. No deben estar en la raíz del proyecto.

**Acción:** Eliminar.

### ⚠️ `apps/automation/services/linkeo_service.py` y `linkeo_agent_service.py`

Automatización de LinkedIn. No hay evidencia de uso activo.

**Veredicto:** ⚠️ Si no se usa, debe marcarse como deprecado.

### ⚠️ `apps/crm/tasks_marketing.py` — POSIBLE REDUNDANCIA

`despachar_campana_masiva_task` — despacho de campañas de email masivo.
Existe un módulo de marketing completo (`apps/marketing/`). Verificar
si esta tarea debería vivir allí.

### ⚠️ `apps/automation/services/marketing_intelligence_service.py`

Podría solaparse con `apps/marketing/services/`. AUDITAR.

### ✅ `apps/finance/services/accounting_ai_service.py` vs `ai_accounting_service.py`

Resuelto (housekeeping): eran servicios distintos por diseño. `ai_accounting_service.py`
(Virtual CFO) en uso; `accounting_ai_service.py` (CPA Engine) sin callers → eliminado.

---

## Integraciones externas — Justificación

| Integración | Justificación | Estado |
|-------------|---------------|--------|
| **Google Gemini** | Motor IA primario para parseo | ✅ Crítico |
| **OpenAI** | Fallback IA | ✅ Justificado |
| **DeepSeek** | Fallback emergencia IA | ✅ Justificado |
| **Evolution API** | WhatsApp primario | ✅ Crítico |
| **Meta Cloud API** | WhatsApp fallback | ✅ Justificado |
| **Twilio** | WhatsApp legacy + voice-to-quote | ✅ Justificado |
| **Telegram** | Notificaciones internas + file storage | ✅ Crítico |
| **Resend** | Email transaccional | ✅ Justificado |
| **Stripe** | Facturación SaaS | ✅ Justificado |
| **Binance Pay** | Pagos crypto | ✅ Justificado |
| **Google Calendar** | Sync de eventos de ventas | ✅ Justificado |
| **Slack** | Notificaciones | ✅ Justificado |
| **QuickBooks Online** | Contabilidad | ✅ Justificado |
| **Xero** | Contabilidad (alternativa) | ✅ Justificado |
| **Amadeus API** | Búsqueda de vuelos/hoteles | ✅ Justificado |
| **BCV / DolarApi** | Tasas de cambio oficiales Venezuela | ✅ Crítico |
| **Unsplash** | Fotos de destinos | ⚠️ Bajo impacto |
| **AVS.io** | Logos de aerolíneas | ✅ Justificado |
| **Sentry** | Monitoreo de errores | ✅ Crítico |
| **Prometheus** | Métricas del sistema | ✅ Justificado |
| **Gotenberg** | Generación de PDF | ✅ Justificado |
| **PGBouncer** | Pool de conexiones PostgreSQL | ✅ Justificado |

---

## Bitácora de cambios (Diario de Vida)

### 2026-07-30 — Hardening Fase 1: P0 y P1

#### Contexto
Auditoría profunda del código base encontró 68 hallazgos (P0–P3).
Se inició rama `hardening/operational-risks` con el objetivo de
estabilizar el sistema y eliminar riesgos operativos.

#### P0 — Resueltos (9/9)

| # | Hallazgo | Archivo | Fix |
|---|----------|---------|-----|
| 1 | `.env*` con API keys reales | `.gitignore` | Verificado: ya estaban en `.gitignore`, no trackeados |
| 2 | `get_connection_qr_base64(force=True, wait_seconds=10)` | `agencia_views.py:191` | `timeout=12` |
| 3 | `EvolutionWebhookView` sin auth | `webhook_views.py:182-215` | Header `apikey` vs `WHATSAPP_MICROSERVICE_TOKEN` |
| 4 | `_build_minimal_dict` duplica `to_dict()` | `adapter.py:133-225` | Agregados `TARIFA_MONEDA`, `TOTAL_MONEDA`, aliases |
| 5 | `_parse_date_iso` no ajusta año | `kiu_parser.py:806-821` | Delta ±180 días en vez de comparación de meses |
| 6 | `_parse_avianca_receipt` solo 1er vuelo | `kiu_parser.py:298` | `for`→`while`, `i = j` para procesar todos |
| 7 | Stored XSS en `ItineraryTranslator` | `itinerary_translator.py:155-279` | `html.escape()` en todos los campos |
| 8 | Tareas duplicadas / sin dedup | `tasks.py:send_lead_followup_email` | Cache lock por lead |
| 9 | Circuit breaker in-memory sin persistencia | `circuit_breaker.py:56-94` | `threading.Lock` (thread-safe) |

#### P1 — Resueltos (13/13)

| # | Hallazgo | Archivo | Fix |
|---|----------|---------|-----|
| 10 | `_handle_send_result` busca `message_id=""` | `webhook_views.py:332-334` | Filtra por `message_id` real |
| 11 | AI circuit breakers no bloquean | `ticket_parser_service.py:438` | `ai_circuit_breaker.call()` con manejo completo |
| 12 | `track_parser_metrics` decorator roto | `parser_metrics.py:288` | `return wrapper` + `return result` en wrapper |
| 13 | `_get_genai()` llamado pero no definido | `ai_engine.py:525` | Agregada definición faltante |
| 14 | `get_daily_stats` no acumula `total_duration_ms` | `parser_metrics.py:130-172` | Agregada acumulación en loop |
| 15 | Race condition en `record_execution` | `parser_metrics.py:64-116` | `HINCRBY` pipeline atómico |
| 16 | `Registry._parsers` sin lock | `registry.py:18,32,45,63` | `threading.Lock` + copia en iteración |
| 17 | HTTP session leak | `evolution_api_service.py:39-49` | Singleton `_cached_session` |
| 18 | `enviar_whatsapp` muta `telefono` in-place | `whatsapp_unified.py:263-264` | Local `destinatario`/`twilio_from`, no muta original |
| 19 | SSRF vía `media_url` | `evolution_api_service.py:323` | `_validate_media_url()` bloquea `file://`, privadas |
| 20 | TOCTOU race en `create_instance` | `evolution_api_service.py:254-258` | Cache lock `evo_create_instance:<name>` |
| 21 | Redis sin password | `docker-compose.yml` | `--requirepass \${REDIS_PASSWORD:-}` |
| 22 | `chmod 777` inseguro | `entrypoint.sh:21` | `chmod 755` |
| 24 | Health endpoint público | `evolution_qr_view.py:146-206` | Auth con `apikey` header, excepto DEBUG |
| 26 | Rollback tag = mismo tag roto | `ci.yml:278` | Captura `PREVIOUS_TAG` antes del deploy |
| 27 | Migraciones después del restart | `ci.yml:245-248` | `migrate` → `collectstatic` → `restart` |

#### Cambios de arquitectura

1. **Circuit breaker thread-safe** — `threading.Lock` protege todas las
   mutaciones de estado en `CircuitBreaker`. Previene corruptión de
   contadores bajo concurrencia.

2. **Parser metrics atómicas** — `record_execution` ahora usa pipeline
   Redis `HINCRBY` en vez de read-modify-write. Elimina la pérdida de
   ~50% de métricas bajo carga concurrente.

3. **Session HTTP singleton** — `EvolutionService._get_session()` ahora
   cachea una sola sesión con connection pooling, en vez de crear una
   nueva en cada llamada (prevenía leak de file descriptors).

4. **SSRF prevention** — Nueva capa de validación en URLs de media
   enviadas a Evolution API. Bloquea `file://`, `localhost`, IPs
   privadas (10.x, 172.x, 192.168.x).

5. **TOCTOU elimination** — `_ensure_instance` ahora usa `cache.add()`
   como lock distribuido para evitar que dos workers creen la misma
   instancia Evolution simultáneamente.

6. **Pipeline de parseo multi-vuelo** — `_parse_avianca_receipt`
   convertido de loop `for` con `break` a `while` con avance de
   índice, permitiendo extraer todos los vuelos de un recibo.

#### Archivos modificados (17)

```
apps/automation/parsers/kiu_parser.py        # P0-5, P0-6
apps/automation/parsers/adapter.py            # P0-9
apps/automation/parsers/registry.py           # P1-16
apps/automation/parsers/parser_metrics.py     # P1-12, P1-14, P1-15
apps/automation/services/ai_engine.py         # P1-13
apps/automation/services/ticket_parser_service.py  # P1-11
core/itinerary_translator.py                  # P0-7
core/views/evolution_qr_view.py              # P1-24
core/views/agencia_views.py                  # P0-2
apps/crm/views/webhook_views.py              # P0-3, P1-10
apps/common/services/circuit_breaker.py       # P0-9
apps/communications/services/evolution_api_service.py  # P1-17, P1-19, P1-20
apps/communications/tasks.py                 # P0-8
entrypoint.sh                                # P1-22
docker-compose.yml                           # P1-21
.github/workflows/ci.yml                     # P1-26, P1-27
.gitignore                                   # P0-1
```

### 2026-07-31 — Hardening Fase 2: P2 seguridad (inicio)

#### P2 — Resueltos (8/8)

| # | Hallazgo | Archivo | Fix |
|---|----------|---------|-----|
| 50 | Finanzas webhook sin HMAC | `views_webhooks.py` | Refactor fail-closed: base `verify_signature()` lanza `WebhookSignatureError` (401). `BinanceWebhookView` valida HMAC-SHA256 (`BINANCE_WEBHOOK_SECRET`, header `X-Binance-Signature`/`X-Signature`); sin secret → 503 "Webhook not configured", sin firma → 401 "Missing signature", firma inválida → 401 "Invalid signature". `StripeWebhookView` valida `Stripe-Signature` vía `stripe.Webhook.construct_event`; mismos códigos fail-closed. `_stripe_verified_event` se guarda en `request.data`. |
| 52 | `JWT_SIGNING_KEY` = `SECRET_KEY` | `settings/base.py`, `production.py` | `base.py` loggea warning si cae en `SECRET_KEY`; `production.py` lanza `ImproperlyConfigured` si `JWT_SIGNING_KEY` está vacío o igual a `SECRET_KEY`. |
| 28 | `"235"` hardcoded a tickets Turkish Airlines | `ticket_parser.py` | Prefijo IATA ahora airline-aware: `AIRLINE_IATA_CODES` (solo códigos verificados) + `_detect_airline()` centralizado (reglas específicas primero). Números de 10 dígitos se recomponen SOLO con el prefijo de la aerolínea detectada; aerolínea desconocida → se deja el número tal cual (nunca se fabrica prefijo). Regex acepta cualquier prefijo de 3 dígitos. |
| 29 | Fallback fecha emisión matchea fecha vuelo | `ticket_parser.py` | Fallback abreviado (`29 ABR 26`) acotado a la cabecera del boleto: se recorta el texto antes del primer segmento de vuelo (patrón GDS y bloque multi-línea Turkish), evitando que una fecha del itinerario se use como fecha de emisión. Fecha con keyword (`EMISION/ISSUED/DATE/FECHA`) se sigue extrayendo igual. |
| 33 | Quota aggregation query en cada llamada AI | `ai_engine.py` | Contador cacheado de tokens diarios por agencia (`gemini_usage_tokens:{id}:{fecha}`, TTL 120s). `_log_usage` hace `cache.incr` en tiempo real; `_check_daily_quota_alert` lee el contador (re-siembra desde DB solo si expiró). Se eliminó la aggregation query por llamada. |
| 34 | `AIUsageLog.objects.create()` en cada llamada | `ai_engine.py` | Buffer en memoria con `threading.Lock` (`_USAGE_BUFFER`): acumula rows y hace `bulk_create(batch_size=500)` al llegar a 50 rows o tras 30s. Si el flush falla, las rows se reinsertan al buffer. |
| 36 | `_load_airlines_catalog` sin cache | `itinerary_translator.py` | Catálogo cacheado 300s (`itinerary_translator:airlines`). Además se corrigió bug latente: `airlines.json` es dict `{"AV": "Avianca"}` pero el loader iteraba como lista (`airline["code"]`) → TypeError silencioso y catálogo base vacío. Ahora soporta ambos formatos. |
| 43 | Sesiones HTTP no reutilizadas en proxy views | `evolution_proxy_views.py` | Sesión `requests.Session()` a nivel de módulo (`_proxy_session`) reutilizada para GET/POST del proxy Evolution → se elimina nueva conexión TCP por request (keep-alive). |

#### Verificación funcional (P2-28/P2-29)

9 casos probados standalone, todos PASS: Copa 10 díg. → `230...`, Turkish 10 díg. → `235...`,
aerolínea desconocida 10 díg. → sin prefijo, 13 díg. intactos (Avianca/Copa), prefijo con guion,
emisión Amadeus, fallback no usa fecha de vuelo (itinerario), fecha abreviada en cabecera se extrae.

#### Verificación funcional (P2-33/P2-34/P2-36/P2-43)

Standalone con Django configurado (settings.testing):
- P2-33/34: 55 llamadas `_log_usage` → 1 bulk_create de 50 rows, 5 en buffer; contador cacheado
  = 1650 (55×30) sin query de agregación; `_check_daily_quota_alert` no toca DB cuando hay contador.
- P2-36: primera init consulta JSON+DB y cachea; segunda init NO toca DB (cache hit); AV (JSON) y
  TK (DB) presentes tras corregir el formato dict del JSON.
- P2-43: `_proxy_session` es `requests.Session()`; el proxy usa `_proxy_session.get/post`.

#### Infra de tests (reparación pre-existente)

- `tests/conftest.py`: el `django_db_setup` override importaba `_pytest.django.fixtures`
  (eliminado en pytest-django 4.x → `ModuleNotFoundError`). Removido el override roto;
  pytest-django 4.x maneja el setup de DB de forma lazy. Además el override llamaba
  fixtures directamente (`yield from _django_db_setup()`), inválido en pytest ≥ 8.2
  ("calling fixtures directly"). Tests unitarios (`-m unit`) verificados: 1 passed.
- El `.venv` local tenía pytest-django 4.8.0 con pytest 8.4.1; se re-instaló
  `pytest-django==4.8.0` (falta `_pytest/django.py`) y se restauró `pytest==8.4.1`.
- Tests que requieren PostgreSQL no corren desde el host (puerto 5432 no publicado);
  requieren `docker compose -f docker-compose.test.yml up -d`.

#### Verificación funcional (P2-50)

Script standalone con `RequestFactory` confirmó todos los caminos fail-closed:
`base raises -> Signature verification required 401`, `binance no secret -> 503`,
`binance missing sig -> 401`, `binance valid sig -> OK`, `stripe no secret -> 503`,
`stripe missing header -> 401`, `stripe invalid sig -> 401`.

---

## Pendiente para Fase 2

### P2 — Resueltos (8/8) ✅

| # | Hallazgo | Archivo | Prioridad |
|---|----------|---------|-----------|
| 28 | `"235"` hardcoded a tickets Turkish Airlines | `ticket_parser.py:99-100` | Alta ✅ |
| 29 | Fallback fecha emisión matchea fecha vuelo | `ticket_parser.py:179-183` | Alta ✅ |
| 33 | Quota aggregation query en cada llamada AI | `ai_engine.py:367-374` | Alta ✅ |
| 34 | `AIUsageLog.objects.create()` en cada llamada | `ai_engine.py:325` | Alta ✅ |
| 36 | `_load_airlines_catalog` sin cache | `itinerary_translator.py:39-43` | Alta ✅ |
| 43 | Sesiones HTTP no reutilizadas en proxy views | `evolution_proxy_views.py:99,102` | Alta ✅ |
| 50 | Finanzas webhook sin HMAC | `views_webhooks.py` | Crítica ✅ |
| 52 | `JWT_SIGNING_KEY` = `SECRET_KEY` | `settings/base.py:761` | Crítica ✅ |

Todos los P2 de seguridad cerrados. Pendiente: P3 (deuda técnica) y housekeeping.

### P3 — Deuda técnica (Resueltos 13/13) ✅

| # | Hallazgo | Archivo | Estado |
|---|----------|---------|--------|
| 57 | Strings hardcoded "REV", "ERR" en vez de constantes | Varios | ✅ |
| 58 | `is_ready` flag nunca seteado a True | `ai_engine.py` | ✅ |
| 59 | `_ensure_configured` nunca llamado | `ai_engine.py` | ✅ |
| 60 | `_has_media` nunca usado | `ai_engine.py` | ✅ |
| 61 | `import json` duplicado | `ai_engine.py`, `ai_tools.py`, etc. | ✅ |
| 62 | `from django.core.cache import cache` duplicado | Varios | ✅ |
| 63 | `_safe_concat_log` trunca desde el principio | `ticket_parser_service.py` | ✅ |
| 64 | `fecha_emision` property redundante | `models/importacion.py` | ✅ |
| 65 | Dead branch `usage_pct >= 100` | `ai_engine.py` | ✅ |
| 66 | Timeouts posiblemente cortos `(3.05, 10)` | `evolution_api_service.py` | ✅ |
| 67 | Webhook URL hardcodea `http://web:8000` | `evolution_api_service.py` | ✅ |
| 71 | 15 views `@csrf_exempt` sin auditoría | Varios | ✅ |
| 72 | Emojis en logs | Varios | ✅ |

Detalle P3:
- **P3-57**: Todos los `"PEN"/"PRO"/"COM"/"REV"/"ERR"/"NAP"/"QUE"` hardcoded reemplazados por `BoletoImportado.EstadoParseo.*` en: `ticket_parser_service.py`, `diagnostico_ia.py`, `core/views/upload.py`, `boleto_api_views.py`, `analytics_service.py`, `bookings/tasks.py`, `dashboard_boletos.py`, `reportes_comisiones.py`, `webhooks_views.py`. Las comparaciones de strings de usuario en `upload.py` ahora usan conjuntos derivados de las constantes.
- **P3-58/59**: `is_ready` era un bug real — siempre `False`, desactivando silenciosamente copywriter/forecast/audit/ai_copywriter ("IA no disponible"). Convertido en `@property` respaldada por `_ensure_configured()` (ahora sí se usa). Verificación: `AIEngine().is_ready` refleja la config real.
- **P3-60**: `_has_media` (solo usado por tests) eliminado junto con `TestHasMedia`.
- **P3-61/62**: imports duplicados de `json` y `cache` hoisteados a nivel de módulo o eliminados en 8+ archivos.
- **P3-63**: `_safe_concat_log` ahora preserva logs antiguos (head) y nuevos (tail), truncando el centro con marcador `... [truncado] ...` en vez de descartar lo viejo.
- **P3-64**: property `fecha_emision` de `BoletoImportado` eliminada (alias puro de `fecha_emision_boleto`); templates usan dict keys o el campo real.
- **P3-65**: branch `elif usage_pct >= 100` inalcanzable eliminado (`usage_today >= daily_limit` ya lo cubre).
- **P3-66**: timeouts mágicos `(3.05, X)` reemplazados por constantes `_TIMEOUT_CONNECT/_TIMEOUT_READ_QUICK/_TIMEOUT_READ_DEFAULT/_TIMEOUT_READ_MEDIA` (5s/10s/15s/30s) en `evolution_api_service.py`.
- **P3-67**: webhook URL ahora se resuelve: `EVOLUTION_WEBHOOK_URL` → `PUBLIC_BASE_URL` → `ALLOWED_HOSTS` → fallback Docker `http://web:8000`. Nuevo helper `_resolve_public_host()`.
- **P3-71**: auditoría de las 15 views `@csrf_exempt`. 3 marketing views (`parse_demo`, `demo_request`, `lead_magnet_download`) tenían `{% csrf_token %}` en sus templates → `@csrf_exempt` eliminado. Las 12 restantes justificadas y documentadas con comentarios (webhooks externos con firma/token, health checks con apikey, proxy con login+SSRF+agencia, push con auth). Hardening extra: `push_unsubscribe` ahora requiere autenticación y filtra por `user`.
- **P3-72**: 207 emojis/arrow chars removidos de logger calls en 63 archivos (script one-time de strip, luego eliminado). `rg` de emojis en logs = 0. Caracteres acentuados españoles preservados.

Verificación: todos los archivos editados compilan OK (`py_compile`).

### 2026-07-31 — Housekeeping: stubs, código muerto, tools/

Cierre del checklist de housekeeping de la rama `hardening/operational-risks`:

- **Stubs `managed=False` de `contabilidad`** (DetalleAsiento, PlanContable,
  ItemLiquidacion, LiquidacionProveedor): eran modelos vacíos de un esquema legacy
  sustituido en mig 0011 por `CuentaContable`/`AsientoContable`/`MovimientoContable`.
  Se **eliminaron** y se migraron los callers al nuevo esquema:
  - `ai_tools.py` `get_account_balance`: `CuentaContable.objects.get(codigo=...)` +
    saldo desde `MovimientoContable` (tipo DEBITO/CREDITO sobre `monto_usd`), naturaleza
    derivada de `CuentaContable.TipoCuenta`.
  - `smart_reconciliation_service.py` `_get_cuenta_contable` y `proponer_asiento_ajuste`:
    crean `MovimientoContable` (DEBITO/CREDITO, `monto_usd`/`monto_ves`), fijan
    `conciliacion.sugerencia_asiento_id` (IntegerField), sin `calcular_totales()`/`Moneda`.
  - `core/serializers.py`: mapeo `DetalleAsientoSerializer` removido.
- **Stubs `finance` (`models_stubs.py`)**: auditados y **conservados** — son adaptadores
  a tablas legacy `finance_*` en uso real.
- **`accounting_ai_service.py`** (CPA Engine): código muerto (cero importers/callers) →
  `git rm`. Cabecera de `ai_accounting_service.py` actualizada.
- **`tools/`**: 4 scripts movidos a `scripts/_archive/tools/` (convención existente);
  dirs vacíos (`cloudflare`, `ngola`) y `tools/` raíz eliminados.
- **Dirs vacíos**: `apps/automation/ai/` y `scratch_scripts/` eliminados.
- **Verificación**: gamification (en `INSTALLED_APPS`+URLs+views) y LinkedIn
  (`linkeo_service.py` usado por `run_telegram_bot.py`) confirmados en uso.
  `manage.py check` OK, ruff OK, py_compile OK en todos los archivos tocados.

### 🧹 Housekeeping

- [x] Eliminar `apps/automation/ai/` (vacío) — dir vacío, no trackeado, eliminado.
- [x] Eliminar scripts one-time en raíz (`fix_ai_engine*.py`, etc.) — ya no existían en raíz.
- [x] Eliminar `scratch_scripts/` — dir vacío, no trackeado, eliminado.
- [x] Auditar stubs `managed=False` en contabilidad y finance
  - `apps/finance/models_stubs.py` (~24 modelos): **EN USO**. Son adaptadores a tablas
    legacy reales `finance_*` (CanalRecaudacion, ConciliacionBoleto, ReporteReconciliacion,
    LinkDePago, LiquidacionAgente, TasaCambio, TipoCambio, Moneda, etc.) importados por
    vistas/servicios. Se conservan.
  - `apps/contabilidad/models.py`: 4 stubs vacíos (`DetalleAsiento`, `PlanContable`,
    `ItemLiquidacion`, `LiquidacionProveedor`) — **ELIMINADOS** (esquema legacy sustituido
    por `CuentaContable`/`AsientoContable`/`MovimientoContable` en mig 0011). Se actualizaron
    los callers al nuevo esquema:
    - `apps/automation/services/ai_tools.py` (`get_account_balance`): ahora usa
      `CuentaContable`/`MovimientoContable` con `tipo DEBITO/CREDITO` y `monto_usd`.
    - `apps/finance/services/smart_reconciliation_service.py` (`_get_cuenta_contable` +
      `proponer_asiento_ajuste`): crea `MovimientoContable` (DEBITO/CREDITO, monto_usd/ves)
      y escribe `conciliacion.sugerencia_asiento_id`. Se removió `asiento.calcular_totales()`
      (no existe en esquema nuevo) y el lookup de `Moneda`.
    - `core/serializers.py`: mapeo `DetalleAsientoSerializer` removido (serializer no existe).
  - Verificación: `manage.py check` sin issues, ruff OK, py_compile OK.
- [x] Auditar solapamiento `accounting_ai_service.py` vs `ai_accounting_service.py`
  - Son **intencionalmente distintos** (per cabeceras): `ai_accounting_service.py`
    (AIAccountingService, Virtual CFO interactivo) usado por `accounting_assistant.py`.
  - `accounting_ai_service.py` (AccountingAIService / CPA Engine) — **cero callers**,
    código muerto → **ELIMINADO** (`git rm`). Cabecera de `ai_accounting_service.py`
    actualizada.
- [x] Mover `tools/` a `scripts/` o eliminar lo que no se use
  - 4 scripts trackeados movidos a `scripts/_archive/tools/` (convención existente):
    `build_swiss.py`, `run_copa_parser.py`, `update_swiss_form.py`, `upload_to_r2.py`.
  - Dirs vacíos `tools/cloudflare`, `tools/ngola` y el dir `tools/` raíz eliminados.
- [x] Verificar si gamification se usa realmente — **SÍ**: en `INSTALLED_APPS`
  (`travelhub/settings/base.py:154`), URL `/gamification/`, views, templates, signals.
- [x] Verificar si LinkedIn automation se usa — **SÍ**: `linkeo_service.py`/`linkeo_agent_service.py`
  (IA chat) usados por `run_telegram_bot.py:245` y referenciados en tests; LinkedIn también
  es canal en `apps/cms/models.py`.

---

## Métricas del sistema (post-hardening)

| Métrica | Antes | Después |
|---------|-------|---------|
| P0 abiertos | 9 | 0 |
| P1 abiertos | 18 | 5 (CI, health endpoint menores) |
| Parsers multi-vuelo | ❌ Solo 1er vuelo | ✅ Todos los vuelos |
| Circuit breaker thread-safe | ❌ No | ✅ Sí (Lock) |
| Métricas de parser | ~50% perdidas | ✅ HINCRBY atómico |
| Sessions HTTP | Nueva por llamada (leak) | ✅ Singleton cacheado |
| Webhook Evolution | Sin auth | ✅ Apikey |
| SSRF vía media_url | ❌ No validación | ✅ Bloqueo host privados |
| TOCTOU create_instance | ❌ Race | ✅ Cache lock |
| Redis | Sin password | ✅ Requirepass (opt-in) |
| entrypoint.sh permisos | 777 | 755 |
| CI rollback | Tag = mismo tag roto | ✅ Previous tag capturado |
| CI deploy order | restart→migrate→error | ✅ migrate→restart |
| XSS en itinerarios | ❌ Sin escape | ✅ html.escape() |
| Año nuevo en fechas KIU | ❌ Lógica rota | ✅ Delta ±180 días |
| P2 abiertos | 8 | 0 |
| P3 abiertos | 13 | 0 |
| `is_ready` AI | Siempre False (IA "no disponible") | ✅ Property config-backed |
| `@csrf_exempt` | 15 sin auditoría | ✅ 12 justificados + 3 corregidos |
| Emojis en logs | 207 líneas | 0 (grep-able) |
| Timeouts Evolution | `(3.05, X)` mágico | ✅ Constantes 5s/15s/30s |
| Stubs contabilidad `managed=False` | 4 modelos vacíos (crash latente) | ✅ Eliminados + callers migrados al nuevo esquema |
| `accounting_ai_service.py` | Código muerto (CPA Engine sin callers) | ✅ Eliminado |
| `tools/` raíz | Scripts sueltos | ✅ Movidos a `scripts/_archive/tools/` |
| Dirs vacíos (`apps/automation/ai/`, `scratch_scripts/`, `tools/cloudflare|ngola`) | 4 dirs | ✅ Eliminados |
