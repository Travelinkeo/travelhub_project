# TravelHub — Plan de Remediación Priorizado

> Auditoría completa del código base — Julio 2026
> 68 hallazgos clasificados en 4 niveles de prioridad

---

## P0 — Inmediato (24h)
*Riesgo de pérdida de datos, 500 error en producción, o breach de seguridad*

| # | Área | Hallazgo | Archivo:Línea |
|---|------|----------|---------------|
| 1 | **Secrets** | `.env.local`, `.env`, `.env.production` commiteados con API keys REALES (Gemini, Telegram, Amadeus, Resend, Google Places, SECRET_KEY) | `.env.*` |
| 2 | **Evolution** | Invalid kwargs en `get_connection_qr_base64(force=True, wait_seconds=10)` — TypeError siempre, QR nunca se fetchea sync | `agencia_views.py:191`, `evolution_qr_view.py:191` |
| 3 | **Webhook** | `EvolutionWebhookView` sin autenticación — cualquier POST externo inyecta datos falsos | `webhook_views.py:182-215` |
| 4 | **Pipeline** | `_build_minimal_dict` duplica 80% de `to_dict()` — fragile divergence | `adapter.py:133-225` |
| 5 | **Pipeline** | `_parse_date_iso` no ajusta año correctamente para vuelos cerca del cambio de año | `kiu_parser.py:806-821` |
| 6 | **Pipeline** | `_parse_avianca_receipt` solo procesa el primer vuelo (temprano `break`) | `kiu_parser.py:298` |
| 7 | **Pipeline** | Stored XSS en `ItineraryTranslator` — datos del ticket incrustados sin escape en HTML | `itinerary_translator.py:155-279` |
| 8 | **Task** | Definiciones duplicadas en `tasks.py` y `tasks/evolution.py` — comportamiento no-determinístico | `tasks.py`, `tasks/evolution.py` |
| 9 | **Circuit Breaker** | In-memory, no persiste entre workers — no protege contra outages reales | `circuit_breaker.py:56-94` |

---

## P1 — Crítica (Esta Semana)
*Riesgo de falla mayor, corrupción de datos o exposición de infraestructura*

| # | Área | Hallazgo | Archivo:Línea |
|---|------|----------|---------------|
| 10 | **Webhook** | `_handle_send_result` busca `message_id=""` — huérfano si múltiples mensajes | `webhook_views.py:332-334` |
| 11 | **Circuit Breaker** | AI: dos circuit breakers independientes, NINGUNO bloquea llamadas realmente | `ai_engine.py:110-113`, `ticket_parser_service.py:438` |
| 12 | **Pipeline** | `track_parser_metrics` decorator `return result` en lugar de `return wrapper` — NameError si se aplica | `parser_metrics.py:288-289` |
| 13 | **Pipeline** | `_get_genai()` llamado pero no definido en `ai_engine.py` | `ai_engine.py:525` |
| 14 | **Pipeline** | `get_daily_stats` nunca acumula `total_duration_ms` — métricas de duración siempre 0 | `parser_metrics.py:130-172` |
| 15 | **Pipeline** | Race condition en `record_execution` — read-modify-write en Redis pierde ~50% de métricas | `parser_metrics.py:64-116` |
| 16 | **Pipeline** | `Registry._parsers` mutable sin lock — `RuntimeError` si muta durante iteración | `registry.py:18,32,45,63` |
| 17 | **Evolution** | `requests.Session` creado en cada llamada, NUNCA cerrado — leak de file descriptors + TCP | `evolution_api_service.py:39-49` |
| 18 | **Evolution** | `enviar_whatsapp` muta `telefono` in-place — `whatsapp:whatsapp:+58...` en retry | `whatsapp_unified.py:263-264` |
| 19 | **Evolution** | SSRF via `media_url` sin validación — atacante puede hacer que Evolution pida `file:///etc/passwd` | `evolution_api_service.py:323` |
| 20 | **Evolution** | TOCTOU race: `if not connected → create_instance` puede crear instancias duplicadas | `evolution_api_service.py:254-258` |
| 21 | **Config** | Redis sin password en docker-compose — acceso no autenticado desde cualquier contenedor | `docker-compose.yml` |
| 22 | **Config** | `entrypoint.sh` hace `chmod 777` en `/app/media` y `/app/boletos_importados` | `entrypoint.sh:21` |
| 23 | **Config** | Evolution DB defaults `evolution:evolution` si env vars no están seteadas | `docker-compose.yml:475` |
| 24 | **Config** | Health endpoint pública enumera todas las agencias activas + su estado WhatsApp | `evolution_qr_view.py:146-206` |
| 25 | **Testing** | ~36 test files (28%) permanentemente SKIPPED — views, APIs, parser coverage no ejecutan | Múltiples `test_*.py` |
| 26 | **Testing** | `ROLLBACK_TAG = sha-${{ github.sha }}` en CI — rollback despliega el mismo tag roto | `.github/workflows/ci.yml:278` |
| 27 | **Testing** | Deploy corre `docker compose up -d` ANTES que `migrate` — schema mismatch temporal | `.github/workflows/ci.yml:245-248` |

---

## P2 — Alta (Este Mes)
*Performance, observabilidad, mantenibilidad — riesgo operacional moderado*

| # | Área | Hallazgo | Archivo: Línea |
|---|------|----------|---------------|
| 28 | **Pipeline** | `harcoded "235"` prepended a números de ticket de 10 dígitos (Turkish Airlines) | `ticket_parser.py:99-100` |
| 29 | **Pipeline** | Fallback genérico de fecha de emisión puede matchear fecha de vuelo | `ticket_parser.py:179-183` |
| 30 | **Pipeline** | KIU `can_parse` falso positivo con términos genéricos (`ISSUE AGENT/AGENTE EMISOR`) | `kiu_parser.py:19-21` |
| 31 | **Pipeline** | `can_parse` purifica texto O(n) veces — 8+ regex passes sobre texto completo | `registry.py:47` |
| 32 | **Pipeline** | `extract_data_from_text` hace doble cache (adapter success + caller) | `ticket_parser.py:355,386` |
| 33 | **Pipeline** | Quota aggregation query en CADA llamada AI — DB load spike en batch | `ai_engine.py:367-374` |
| 34 | **Pipeline** | `AIUsageLog.objects.create()` en CADA llamada — 1000 rows por batch | `ai_engine.py:325` |
| 35 | **Pipeline** | `BoletoImportado.save()` SELECT extra en cada save | `importacion.py:329` |
| 36 | **Pipeline** | `_load_airlines_catalog` carga TODAS las aerolíneas sin cache | `itinerary_translator.py:39-43` |
| 37 | **Pipeline** | `_find_provider` itera en Python sin `limit` — memoria | `persistence.py:132-147` |
| 38 | **Pipeline** | `_extract_foid` puede matchear teléfonos o zip codes | `kiu_parser.py:132-142` |
| 39 | **Pipeline** | Patrón compacto de fecha `\d{2}[A-Z]{3}\d{2}` demasiado genérico | `kiu_parser.py:452` |
| 40 | **Pipeline** | Lógica IVA/tax frágil — `iva_amt > tax_amt` descarta total original | `kiu_parser.py:374-433` |
| 41 | **Pipeline** | `METRICS_TTL` definido pero nunca usado (hardcoded 30 días) | `parser_metrics.py:43` |
| 42 | **Pipeline** | `ParserMetrics.feature` como atributo dinámico sin field en dataclass | `parser_metrics.py:22-33` |
| 43 | **Evolution** | Sesiones HTTP no reutilizadas en proxy views — nueva conexión TCP por request | `evolution_proxy_views.py:99,102` |
| 44 | **Evolution** | Nonce injection frágil — `string.replace` sin considerar variantes HTML | `evolution_proxy_views.py:140-147` |
| 45 | **Evolution** | Cache TTL mismatch: webhook QR setea 300s, otros lugares 120s | `webhook_views.py:364` |
| 46 | **Evolution** | `fetch_evolution_qr_task` Socket.IO/WebSocket fallbacks sin `try/finally` — leak de conexión | `tasks.py:1364-1369` |
| 47 | **Evolution** | Beat: 1 task por agencia cada 60s — 100 agencias = 100 tasks/min | `celery_beat_schedule.py:86-90` |
| 48 | **Evolution** | `process_scheduled_whatsapp_messages` no usa `select_for_update()` — race en 60s cycles | `tasks.py:1396-1403` |
| 49 | **Security** | CSP removido por completo para `/system/whatsapp/qr/` — clickjacking | `middleware.py:400-406` |
| 50 | **Security** | Finanzas webhook público sin HMAC — cualquiera forja pagos | `views_webhooks.py:23` |
| 51 | **Security** | `push_unsubscribe` sin auth — atacante desuscribe push notifications | `push_views.py:51` |
| 52 | **Security** | `JWT_SIGNING_KEY` = `SECRET_KEY` por defecto | `settings/base.py:761` |
| 53 | **Testing** | `conftest.py` 607 líneas — complejidad, monkeypatching frágil | `tests/conftest.py` |
| 54 | **Testing** | Duplicado `mock_ai_engine` fixture en `tests/conftest.py` y `core/tests/conftest.py` | Ambos conftest |
| 55 | **Testing** | Ruff target conflict: `.ruff.toml` py313 vs `pyproject.toml` py312 | `.ruff.toml`, `pyproject.toml` |
| 56 | **Testing** | E2E test de venta no verifica DB — solo checkea URL | `test_flow_01_venta.py` |

---

## P3 — Media (Próximo Trimestre)
*Mejora continua, deuda técnica, refactors*

| # | Área | Hallazgo |
|---|------|----------|
| 57 | **Pipeline** | Hardcoded strings `"REV"`, `"ERR"` en vez de constantes del modelo |
| 58 | **Pipeline** | `is_ready` flag nunca seteado a True — dead code |
| 59 | **Pipeline** | `_ensure_configured` nunca llamado — dead code |
| 60 | **Pipeline** | `_has_media` nunca usado — dead code |
| 61 | **Pipeline** | `import json` duplicado en `ai_engine.py` |
| 62 | **Pipeline** | `from django.core.cache import cache` duplicado en `ai_engine.py` |
| 63 | **Pipeline** | `_safe_concat_log` trunca del principio (pierde logs más viejos = más útiles) |
| 64 | **Pipeline** | `fecha_emision` property en BoletoImportado redundante |
| 65 | **Pipeline** | Dead branch `usage_pct >= 100` matemáticamente inalcanzable |
| 66 | **Evolution** | Timeouts posiblemente cortos (`(3.05, 10)` para send_text) |
| 67 | **Evolution** | Webhook URL hardcodea `http://web:8000` — solo válido en Docker |
| 68 | **Testing** | `test_minimal.py` archivo trivial `assert True` — remover |
| 69 | **Testing** | Terraform sin backend config ni `terraform.tfvars` — no funcional |
| 70 | **Testing** | Helm `values.yaml` placeholder `myregistry/travelhub` |
| 71 | **General** | 15 views `@csrf_exempt` — inventario sin auditoría formal |
| 72 | **General** | Emojis en logs — dificulta grep y parsing automatizado |

---

## Plan de Acción — Primera Semana

### Día 1: Fuego (P0)
1. **Rotar TODAS las API keys commiteadas** y agregar `.env*` a `.gitignore`
2. Fix `get_connection_qr_base64(force, wait_seconds)` → quitar kwargs inválidos
3. Agregar HMAC/API key a `EvolutionWebhookView`
4. Eliminar `break` temprano en `_parse_avianca_receipt` (H4)
5. Fix `_parse_date_iso` year boundary logic (C8)
6. Unificar definiciones duplicadas de tareas (tasks.py vs evolution.py)

### Día 2: Seguridad (P1)
7. Agregar password a Redis containers
8. Cambiar `chmod 777` → `chmod 755` + ownership explícito en entrypoint.sh
9. Agregar auth a endpoints de salud pública
10. Fix rollback tag en CI
11. Reordenar deploy CI: migrate → restart
12. Poner sessions HTTP en `EvolutionService` como singleton + context manager

### Día 3: Pipeline estable (P1)
13. Unificar circuit breakers de AI: Redis-backed, realmente bloqueante
14. Fix `_handle_send_result` — usar correlation ID único
15. Fix `Registry._parsers` thread-safety
16. Fix `record_execution` race condition → Redis HINCRBY
17. Agregar `select_for_update()` en `process_scheduled_whatsapp_messages`

### Día 4-5: Testing (P1-P2)
18. Revisar y activar ~20 test files skipped por "refactorización pendiente"
19. Agregar test para Avianca receipt parser con fixture real
20. Parser metrics: fix `track_parser_metrics`, `total_duration_ms`, `METRICS_TTL`
21. Cubrir con test al menos 3 escenarios de error: QR falla, webhook sin auth, send_text timeout

### Semana 2-4: Performance + Deuda Técnica (P2)
22. Refactor `_build_minimal_dict` y `to_dict` → shared utility
23. Cache aerolíneas en Redis
24. Batch `AIUsageLog` en lugar de INSERT por llamada
25. Cache quota aggregation en Redis
26. Unificar TTL de QR cache (120s en todos lados)
27. Fix doble caché en extract_data_from_text
