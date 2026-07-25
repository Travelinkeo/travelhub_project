"""Módulo evolution de la aplicación common.
"""

import datetime
import json
import logging
import os

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)

_WHATSAPP_HEALTH_LAST_STATE_KEY = "monitor:whatsapp_health:last_state"
_WHATSAPP_HEALTH_LAST_STATE_TTL = 3600  # 1 hora de gracia (evita reset)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=60,
    soft_time_limit=50,
)
def send_evolution_message_task(self, agencia_id, phone_number, text):
    # send_evolution_message_task: Envía  evolution message task. Args: datos del mensaje. Returns: resultado del envío.
    from apps.communications.services.whatsapp_service import WhatsAppEvolutionService

    try:
        service = WhatsAppEvolutionService(agencia_id)
        success = service.send_message(phone_number, text)
        if success:
            logger.info(f"Evolution message sent (agencia={agencia_id}, to={phone_number})")
        else:
            logger.warning(f"Evolution message failed (agencia={agencia_id}, to={phone_number})")
        return success
    except Exception as exc:
        logger.error(f"Evolution message task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    bind=True,
    queue="notifications",
    max_retries=3,
    default_retry_delay=30,
    time_limit=120,
    soft_time_limit=100,
)
def send_evolution_document_task(
    self, agencia_id, phone_number, document_url, filename, caption=""
):
    # send_evolution_document_task: Envía  evolution document task. Args: datos del mensaje. Returns: resultado del envío.
    from apps.communications.services.whatsapp_service import WhatsAppEvolutionService

    try:
        service = WhatsAppEvolutionService(agencia_id)
        success = service.send_document(phone_number, document_url, filename, caption)
        if success:
            logger.info(f"Evolution document sent (agencia={agencia_id}, to={phone_number})")
        else:
            logger.warning(f"Evolution document failed (agencia={agencia_id}, to={phone_number})")
        return success
    except Exception as exc:
        logger.error(f"Evolution document task error: {exc}")
        self.retry(exc=exc)


@shared_task(
    name="apps.common.tasks.fetch_all_qr_codes_task",
    queue="default",
    time_limit=120,
    soft_time_limit=100,
)
def fetch_all_qr_codes_task():
    """Renueva el QR de WhatsApp para todas las agencias con Evolution configurado.

    Se ejecuta periódicamente por Celery Beat. Por cada agencia activa con un
    subdominio_slug configurado, dispara fetch_evolution_qr_task en paralelo.
    Solo dispara fetch si la instancia NO está ya conectada.
    """
    from core.models.agencia import Agencia

    # subdominio_slug vive en AgenciaConfiguracion, usamos el ORM correcto
    agencias = (
        Agencia.objects.filter(activa=True)
        .select_related("configuracion")
        .filter(configuracion__subdominio_slug__isnull=False)
        .exclude(configuracion__subdominio_slug="")
    )
    total = 0
    for ag in agencias:
        slug = ag.subdominio_slug
        if slug:
            fetch_evolution_qr_task.delay(slug)
            total += 1

    logger.info(f"fetch_all_qr_codes_task: despachadas {total} tareas de QR para agencias activas.")
    return total


@shared_task(
    bind=True,
    queue="default",
    max_retries=2,
    default_retry_delay=5,
    time_limit=60,
    soft_time_limit=50,
)
def fetch_evolution_qr_task(self, instance_name):
    """Fetch QR code for an Evolution instance and cache it.

    This task retrieves the QR (base64) from the Evolution API via HTTP and stores
    it in Redis for 2 minutes. It replaces the previous incorrectly‑bound task
    definition that prevented execution.
    """

    import requests
    from django.core.cache import cache

    from apps.communications.services.evolution_api_service import EvolutionService

    cache_key = f"evo_qr:{instance_name}"

    # 1. Si ya está conectado, no necesitamos el QR y evitamos tocar la API de conexión
    if EvolutionService.get_connection_status(instance_name):
        logger.info(f"Instancia '{instance_name}' ya está conectada. Omitiendo fetch de QR.")
        cache.delete(cache_key)
        return None

    try:
        base_url = EvolutionService._get_base_url()
        headers = EvolutionService._get_headers()
        # The GET endpoint does not expect a JSON payload, so drop the Content-Type header.
        headers.pop("Content-Type", None)
        response = requests.get(
            f"{base_url}/instance/connect/{instance_name}", headers=headers, timeout=15
        )
        if response.status_code == 404:
            logger.info(f"Instance '{instance_name}' not found. Attempting to create...")
            EvolutionService.create_instance(instance_name)
            response = requests.get(
                f"{base_url}/instance/connect/{instance_name}", headers=headers, timeout=15
            )
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get("base64"):
                cache.set(cache_key, data["base64"], 300)  # 5 minutos
                logger.info(f"Evolution QR cached via HTTP for {instance_name}")
                return data["base64"]
    except (requests.RequestException, json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to fetch Evolution QR for {instance_name}: {e}")
        return None

    try:
        import websocket

        ws_url = base_url.replace("http://", "ws://")
        ws_url = f"{ws_url}/{instance_name}"
        ws_headers = {"apikey": headers.get("apikey", "")}

        ws = websocket.create_connection(ws_url, header=ws_headers, timeout=2)
        for _ in range(10):
            try:
                message = ws.recv()
                data = json.loads(message)
                event = data.get("event", "")
                qr = data.get("qrcode", data if event else {})
                if isinstance(qr, dict) and qr.get("base64"):
                    cache.set(cache_key, qr["base64"], 120)
                    logger.info(f"Evolution QR cached via WebSocket for {instance_name}")
                    ws.close()
                    return qr["base64"]
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        ws.close()
    except ImportError:
        logger.warning("websocket module not available for QR fetch")
    return None


@shared_task(
    name="apps.common.tasks.process_scheduled_whatsapp_messages",
    queue="default",
    time_limit=120,
    soft_time_limit=100,
)
def process_scheduled_whatsapp_messages():
    """Envía los mensajes de WhatsApp programados cuya hora ya llegó.

    Se ejecuta cada minuto vía Celery Beat. Busca mensajes en estado
    'scheduled' con programado_para <= ahora y los envía.
    """
    from django.utils import timezone

    from apps.crm.models import WhatsAppScheduledMessage

    now = timezone.now()
    pendientes = WhatsAppScheduledMessage.objects.filter(
        estado="scheduled", programado_para__lte=now
    ).select_related("agencia", "cliente")

    enviados = 0
    for msg in pendientes:
        msg.estado = "sending"
        msg.save(update_fields=["estado"])

        try:
            instance_name = f"agencia_{msg.agencia_id}"
            if msg.agencia and hasattr(msg.agencia, "configuracion"):
                cfg = msg.agencia.configuracion
                if cfg.evolution_instance_name:
                    instance_name = cfg.evolution_instance_name

            from apps.communications.services.evolution_api_service import EvolutionService

            exito = EvolutionService.send_text(instance_name, msg.telefono, msg.texto)

            if exito:
                from apps.crm.models import MensajeWhatsApp

                m = MensajeWhatsApp.objects.create(
                    cliente=msg.cliente,
                    direccion="OUT",
                    texto=msg.texto,
                    estado="sent",
                    tipo_mensaje="text",
                    agencia=msg.agencia,
                )
                msg.mensaje_resultante = m
                msg.estado = "sent"
                msg.save(update_fields=["estado", "mensaje_resultante"])
                enviados += 1
            else:
                msg.estado = "failed"
                msg.error_msg = "Error al enviar vía Evolution"
                msg.save(update_fields=["estado", "error_msg"])
        except Exception as e:
            msg.estado = "failed"
            msg.error_msg = str(e)[:500]
            msg.save(update_fields=["estado", "error_msg"])
            logger.error(f"Error enviando WA programado #{msg.pk}: {e}")

    if pendientes:
        logger.info(f"Mensajes WA programados procesados: {enviados}/{len(pendientes)} enviados")
    return enviados


@shared_task(name="apps.common.tasks.monitor_whatsapp_health_task", queue="default", time_limit=60)
def monitor_whatsapp_health_task():
    """Monitor proactivo del flujo WhatsApp/Evolution. Alerta a Telegram si down/degraded."""
    from django.core.cache import cache

    # 1. Llamar al endpoint interno en lugar de re-implementar la lógica
    # Calculamos el host Django correctamente desde settings.
    # Como esto corre en web container, apuntamos a localhost:8000.
    django_base = "http://localhost:8000"
    health_url = f"{django_base}/system/whatsapp/health/"

    started_ts = datetime.datetime.now(datetime.UTC)
    health_data = None
    http_status = None

    try:
        import requests

        # Backend URL desde settings Django
        django_base = (
            getattr(settings, "DJANGO_BASE_URL", None)
            or os.getenv("DJANGO_BASE_URL")
            or "http://localhost:8000"
        )
        health_url = f"{django_base}/system/whatsapp/health/"

        # Generar headers de service-account si existen
        headers = {"User-Agent": "travelhub-monitor/1.0"}
        service_token = os.getenv("MONITOR_SERVICE_TOKEN")
        if service_token:
            headers["Authorization"] = f"Bearer {service_token}"

        response = requests.get(health_url, headers=headers, timeout=30)
        http_status = response.status_code
        if response.status_code == 200:
            health_data = response.json()
        else:
            health_data = {"error": f"HTTP {http_status}", "raw": response.text[:500]}
    except Exception as e:
        logger.exception("monitor_whatsapp_health_task: error fetching health endpoint")
        health_data = {"error": str(e), "status": "down"}

    # 2. Evaluar estado
    overall = (health_data or {}).get("status", "down")
    checks = (health_data or {}).get("checks", {})

    # 3. Construir resumen
    if overall == "ok":
        summary = "✅ Todos los flujos WhatsApp OK"
    else:
        affected = [
            f"• {slug}: {info.get('status')} (state={info['checks'].get('evolution_state')}, qr_gen={info['checks'].get('qr_generable')})"
            for slug, info in checks.items()
        ]
        summary = (
            f"❌ Estado: <b>{overall.upper()}</b>\n"
            + ("Instances afectadas:\n" + "\n".join(affected) if affected else "")
            + f"\nDebug: `{django_base.rstrip('/')}/system/whatsapp/health/`"
        )

    # 4. Resumir performance
    overall_ms = (health_data or {}).get("overall_ms", "?")

    # 5. Detectar cambios de estado para evitar spam
    last_state = cache.get(_WHATSAPP_HEALTH_LAST_STATE_KEY)
    alert_needed = last_state != overall and overall in ("degraded", "down")

    if not alert_needed:
        # Loggear igual para auditoría
        logger.info(
            "monitor_whatsapp_health: state=%s elapsed_ms=%s affected=%d",
            overall,
            overall_ms,
            len(checks),
        )
        cache.set(_WHATSAPP_HEALTH_LAST_STATE_KEY, overall, _WHATSAPP_HEALTH_LAST_STATE_TTL)
        return {"status": overall, "alert_sent": False, "overall_ms": overall_ms}

    # 6. Construir mensaje de Telegram
    elapsed = (datetime.datetime.now(datetime.UTC) - started_ts).total_seconds()
    telegram_msg = (
        f"🚨 <b>WhatsApp Health Alert</b>\n"
        f"⏰ {started_ts.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        f"⏱ Verificado en {elapsed:.2f}s ({overall_ms}ms en endpoint)\n"
        f"\n{summary}"
    )

    # 7. Enviar alerta (USAR SEND TELEGRAM TASK para no bloquear)
    try:
        from django.conf import settings as dj_settings

        from apps.common.tasks import send_telegram_task

        admin_chat_id = getattr(dj_settings, "TELEGRAM_ADMIN_ID", None)
        if admin_chat_id:
            send_telegram_task.delay(telegram_msg, chat_id=str(admin_chat_id))
            logger.error(
                "monitor_whatsapp_health: Alert sent to Telegram admin=%s state=%s",
                admin_chat_id,
                overall,
            )
        else:
            logger.warning(
                "monitor_whatsapp_health: state=%s but TELEGRAM_ADMIN_ID not configured",
                overall,
            )
    except Exception as e:
        logger.error("monitor_whatsapp_health: error sending telegram alert: %s", e)

    # 7b. Log a Sentry también si está disponible
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            scope.set_tag("component", "whatsapp_monitor")
            scope.set_tag("state", overall)
            scope.set_extra("health_data", health_data)
            sentry_sdk.capture_message(
                f"whatsapp health {overall}",
                level="error" if overall == "down" else "warning",
            )
    except Exception as exc:
        logger.warning("sentry_sdk no disponible para alerta de health: %s", exc)

    # 8. Update cache con nuevo estado
    cache.set(_WHATSAPP_HEALTH_LAST_STATE_KEY, overall, _WHATSAPP_HEALTH_LAST_STATE_TTL)

    kpis = {
        "ok": sum(1 for c in checks.values() if c.get("status") == "ok"),
        "degraded": sum(1 for c in checks.values() if c.get("status") == "degraded"),
        "down": sum(1 for c in checks.values() if c.get("status") == "down"),
    }

    return {
        "status": overall,
        "alert_sent": alert_needed,
        "overall_ms": overall_ms,
        "instances": kpis,
    }
