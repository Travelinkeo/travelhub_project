# Async Refactoring Progress

## Goal
Move sync HTTP calls (Evolution API, Meta API, Twilio, Binance, IA pipelines) out of Django request-response cycle into Celery workers.

## Key Principles
- Use Celery with Redis broker; queues: `notifications`, `ia_fast`, `default`.
- Tasks: `bind=True`, `queue`, `max_retries`, `time_limit`.
- Payment webhooks (Stripe/Binance) stay sync by design (`select_for_update()` + fast DB ops).
- Management commands stay sync (CLI context).
- `select_related()`/`prefetch_related()` used in tasks to avoid extra queries.

## Completed

### 7 new Celery tasks (`apps/common/tasks.py`)
| Task | Queue | Purpose |
|------|-------|---------|
| `send_email_task` | `notifications` | Send email async |
| `enviar_bienvenida_agencia_task` | `notifications` | Agency welcome email |
| `notificar_confirmacion_pago_task` | `notifications` | Payment confirmed notification |
| `notificar_recordatorio_pago_task` | `notifications` | Payment reminder |
| `notificar_boleto_procesado_task` | `notifications` | Ticket processed notification |
| `process_twilio_voice_quote_task` | `ia_fast` | Twilio voice → transcription → AI → WhatsApp quote |
| `fetch_evolution_qr_task` | `default` | Fetch Evolution QR via HTTP/WebSocket |

### Files migrated

#### `apps/communications/services/notification_dispatcher.py`
- `EmailChannel.send()` → `send_email_task.delay()` instead of calling `enviar_email_generico()` sync
- `WhatsAppChannel.send()` → `send_whatsapp_task.delay()` instead of calling `enviar_whatsapp()` sync
- `notificar_boleto_procesado()` admin WhatsApp → `send_whatsapp_task.delay()`
- `enviar_recordatorio_vuelo()` → `send_whatsapp_task.delay()`
- `handle_urgent_notification()` → `send_whatsapp_task.delay()`

#### `core/signals.py`
- `_notificar_pago()` → dispatches `notificar_confirmacion_pago_task.delay()` (was calling `notificar_confirmacion_pago()` sync)

#### `apps/bookings/services/boleto_service.py`
- `post_parse_automation()` → dispatches `notificar_boleto_procesado_task.delay()` (was calling sync)

#### `apps/finance/services/stripe_service.py`
- `_send_welcome_email()` → dispatches `enviar_bienvenida_agencia_task.delay()` (was calling sync)

#### `core/views/webhooks_views.py`
- `ResendInboundWebhookView` → dispatches `parsear_boleto_individual.delay()`, returns 202 (was sync)

#### `apps/cotizaciones/views_whatsapp.py`
- `IncomingWhatsAppWebhook` → dispatches `process_twilio_voice_quote_task.delay()`, returns immediate empty XML (was running full sync AI pipeline)

#### `apps/crm/views/webhook_views.py`
- `WhatsAppWebhookView` → removed sync Celery fallback (`procesar_mensaje_entrante()`); only logs error on Celery unavailability

#### `apps/cotizaciones/views.py`
- `MagicQuoterAIView` → added Django cache wrapping around Unsplash API call (TTL 86400s)

#### `core/views/evolution_qr_view.py`
- `start_qr_fetcher()` → replaced raw `threading.Thread` with `fetch_evolution_qr_task.delay()`; removed all requests/websocket code

#### `apps/finance/views/payment_views.py`
- `BinanceOrderCreateView` → dispatches `create_binance_order_task.delay()`; returns loading page with HTMX auto-refresh; reads cached result on subsequent requests
- Removed unused `requests` import

### Other improvements
- `core/views/health_views.py`: Gotenberg health check timeout 5s→3s

## Intentionally Sync (by design)
- `core/views/evolution_proxy_views.py`: reverse proxy pattern, can't be async in WSGI
- Payment webhooks (Stripe/Binance): `select_for_update()` pattern, fast DB writes
- Management commands: CLI execution, no request context

## Pending
1. `apps/finance/views/payment_views.py` — verify `pago.monto`, `pago.moneda`, `pago.merchant_trade_no` attributes exist on the Pago model (cache dict uses these keys)
2. Restart Celery containers after deploy to register new tasks
3. Monitor logs for import/execution errors

## Deployment
- No container rebuild needed; files copied via `docker compose cp` → container restart
- Modified containers: `celery_worker`, `web`, `celery_beat`
