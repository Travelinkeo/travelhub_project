"""
Webhook Dispatcher — envío asíncrono de eventos a URLs registradas.

Usa Celery para envío no bloqueante con reintentos exponenciales.
"""

import json
import logging
import time
from typing import Any

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


def dispatch_webhook_event(event_type: str, payload: dict[str, Any], agencia_id: int | None = None):
    """
    Despacha un evento a todos los webhooks suscritos.

    Args:
        event_type: Tipo de evento (Ej: "venta.creada")
        payload: Datos del evento
        agencia_id: Filtrar por agencia (None = todas)
    """
    from core.models.webhooks import Webhook

    qs = Webhook.objects.filter(is_active=True)
    if agencia_id:
        qs = qs.filter(agencia_id=agencia_id)

    for webhook in qs.iterator():
        if not webhook.matches_event(event_type):
            continue

        # Enviar asíncronamente via Celery
        send_webhook_task.delay(
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
        )


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
    rate_limit="10/m",  # Max 10 envíos por minuto por worker
)
def send_webhook_task(self, webhook_id: int, event_type: str, payload: dict):
    """
    Envía un webhook individual con firma HMAC y reintentos.

    Reintentos: 30s, 90s, 270s (exponencial).
    """
    import requests

    from core.models.webhooks import Webhook, WebhookDelivery

    try:
        webhook = Webhook.objects.get(id=webhook_id, is_active=True)
    except Webhook.DoesNotExist:
        logger.debug(f"Webhook {webhook_id} no existe o fue desactivado")
        return

    # Preparar payload firmado
    full_payload = {
        "event": event_type,
        "timestamp": timezone.now().isoformat(),
        "agencia_id": webhook.agencia_id,
        "data": payload,
    }
    payload_bytes = json.dumps(full_payload, default=str).encode()
    signature = webhook.sign_payload(payload_bytes)

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature}",
        "X-Webhook-Event": event_type,
        "User-Agent": "TravelHub-Webhook/1.0",
    }

    start_time = time.time()

    try:
        response = requests.post(
            webhook.url,
            data=payload_bytes,
            headers=headers,
            timeout=10,
        )
        duration_ms = int((time.time() - start_time) * 1000)
        success = 200 <= response.status_code < 300

        # Registrar entrega
        WebhookDelivery.objects.create(
            webhook=webhook,
            event_type=event_type,
            payload=full_payload,
            response_status=response.status_code,
            response_body=response.text[:1000],
            success=success,
            duration_ms=duration_ms,
        )

        if success:
            webhook.record_success()
            logger.debug(
                f"Webhook enviado: {event_type} → {webhook.url} "
                f"({response.status_code}, {duration_ms}ms)"
            )
        else:
            webhook.record_failure()
            logger.warning(
                f"Webhook falló: {event_type} → {webhook.url} (status={response.status_code})"
            )
            # Reintentar en error de servidor
            if response.status_code >= 500:
                raise self.retry(
                    exc=requests.HTTPError(f"Status {response.status_code}"),
                    countdown=30 * (2**self.request.retries),
                )

    except requests.RequestException as e:
        duration_ms = int((time.time() - start_time) * 1000)
        webhook.record_failure()

        WebhookDelivery.objects.create(
            webhook=webhook,
            event_type=event_type,
            payload=full_payload,
            success=False,
            error_message=str(e)[:1000],
            duration_ms=duration_ms,
        )

        logger.warning(f"Webhook error: {event_type} → {webhook.url}: {e}")
        raise self.retry(exc=e, countdown=30 * (2**self.request.retries)) from e


# Convenience functions para eventos comunes


def notify_venta_creada(venta):
    """Evento: venta.creada"""
    dispatch_webhook_event(
        "venta.creada",
        {
            "venta_id": venta.id,
            "numero": getattr(venta, "numero", None),
            "monto_total": str(getattr(venta, "monto_total", 0)),
            "moneda": getattr(venta, "moneda", "USD"),
            "cliente": getattr(venta, "cliente_nombre", None),
            "estado": getattr(venta, "estado", None),
        },
        agencia_id=getattr(venta, "agencia_id", None),
    )


def notify_pago_confirmado(pago):
    """Evento: pago.confirmado"""
    dispatch_webhook_event(
        "pago.confirmado",
        {
            "pago_id": pago.id,
            "monto": str(getattr(pago, "monto", 0)),
            "moneda": getattr(pago, "moneda", "USD"),
            "metodo": getattr(pago, "metodo_pago", None),
            "venta_id": getattr(pago, "venta_id", None),
        },
        agencia_id=getattr(pago, "agencia_id", None),
    )


def notify_boleto_importado(boleto):
    """Evento: boleto.importado"""
    dispatch_webhook_event(
        "boleto.importado",
        {
            "boleto_id": boleto.id,
            "aerolinea": getattr(boleto, "aerolinea_codigo", None),
            "pasajero": getattr(boleto, "pasajero_nombre", None),
            "ruta": getattr(boleto, "ruta_completa", None),
            "fecha": str(getattr(boleto, "fecha_emision", "")),
        },
        agencia_id=getattr(boleto, "agencia_id", None),
    )
