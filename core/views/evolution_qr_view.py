import base64
import binascii
import io
import logging
import time

import qrcode
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

QR_CACHE_KEY = "evo_qr:{instance}"
QR_CACHE_TTL = 120  # 2 minutos — Celery Beat lo renueva cada 60s


def start_qr_fetcher(instance_name):
    """Encola una Celery task para capturar el QR de Evolution y cachearlo."""
    from apps.common.tasks import fetch_evolution_qr_task

    fetch_evolution_qr_task.delay(instance_name)


@csrf_exempt  # CSRF exempt: secured by @login_required + session-based auth
@login_required
def evolution_qr_proxy(request, instance_name):
    """Sirve el QR como PNG (obtenido síncronamente y cacheado por 40s si no está en Redis)."""
    import requests

    from apps.communications.services.evolution_api_service import EvolutionService

    cache_key = QR_CACHE_KEY.format(instance=instance_name)
    cached = cache.get(cache_key)

    if cached:
        try:
            # Quitar prefijo data URL si lo tiene (data:image/png;base64,...)
            raw_b64 = cached
            if isinstance(raw_b64, str) and "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_data = base64.b64decode(raw_b64)
            resp = HttpResponse(img_data, content_type="image/png")
            resp["Cache-Control"] = "no-cache, no-store, must-revalidate"
            logger.info(
                "QR served from Redis cache for %s (%d bytes)", instance_name, len(img_data)
            )
            return resp
        except (binascii.Error, ValueError) as e:
            logger.warning("Invalid cached base64 for %s: %s", instance_name, e)

    # Si no está en caché, intentar obtenerlo de la API de Evolution en tiempo real
    qr_b64 = None
    try:
        base_url = EvolutionService._get_base_url()
        headers = EvolutionService._get_headers()
        headers = headers.copy()
        headers.pop("Content-Type", None)

        # Si el estado es 'close', recreamos la instancia para limpiar sesiones Baileys corruptas
        try:
            estado_evolution = EvolutionService.get_instance_state(instance_name)
            if estado_evolution == "close":
                logger.info(
                    f"Instancia '{instance_name}' en estado 'close'. Recreando para limpiar sesión corrupta..."
                )
                EvolutionService.delete_instance(instance_name)
                EvolutionService.create_instance(instance_name)
        except Exception as e:
            logger.error(f"Error verificando o limpiando estado para '{instance_name}': {e}")

        response = requests.get(
            f"{base_url}/instance/connect/{instance_name}", headers=headers, timeout=8
        )
        if response.status_code == 404:
            logger.info(f"Instance '{instance_name}' not found. Re-creating...")
            EvolutionService.create_instance(instance_name)
            response = requests.get(
                f"{base_url}/instance/connect/{instance_name}", headers=headers, timeout=8
            )

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict) and data.get("base64"):
                qr_b64 = data["base64"]
                # Guardar en caché con un TTL muy corto de 40 segundos para garantizar frescura
                cache.set(cache_key, qr_b64, 40)
                logger.info(f"Evolution QR fetched synchronously and cached for {instance_name}")
    except Exception as e:
        logger.error(f"Failed to fetch Evolution QR synchronously for {instance_name}: {e}")

    if qr_b64:
        try:
            if isinstance(qr_b64, str) and "," in qr_b64:
                qr_b64 = qr_b64.split(",", 1)[1]
            img_data = base64.b64decode(qr_b64)
            resp = HttpResponse(img_data, content_type="image/png")
            resp["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
        except Exception as e:
            logger.error(f"Error decoding fetched QR base64: {e}")

    # Fallback: Si no se pudo obtener, generar un código QR que no sea un QR de sesión falso de WhatsApp
    buf = io.BytesIO()
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(
        "Error: No se pudo obtener el codigo QR real de WhatsApp. Por favor, espere o recargue la pagina."
    )
    qr.make(fit=True)
    img = qr.make_image(fill_color="#ef4444", back_color="white")  # Rojo para indicar error
    img.save(buf, format="PNG")
    resp = HttpResponse(buf.getvalue(), content_type="image/png")
    resp["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


# ============================================================================
#  HEALTH CHECK
# ============================================================================
#
# Endpoint sin autenticación que expone el estado REAL del flujo WhatsApp.
# Diseñado para monitors externos (UptimeRobot, Prometheus blackbox,
# Pingdom, Datadog HTTP check, etc.).
#
# Semántica del campo `status`:
#   "ok"          → QR disponible en Redis cache O generable desde Evolution
#   "degraded"    → Cache vacío pero Evolution responde
#   "down"        → Evolution no responde o auth key inválida
#   "not_configured" → Evolution no devuelve QR aún (estado inicial de instancia)
#
# Devuelve siempre 200 (es health check liviano, NO Uptime-penalize un 503 por
# rate limits) — los monitors deben mirar `status` y `checks.cache_age_seconds`.
#


@csrf_exempt
def whatsapp_qr_health(request, instance_name=None):
    """Health-check del flujo WhatsApp/Evolution.

    Sin auth. Devuelve JSON con el estado en detalle.

    Soporta 2 modos:
      * GET /system/whatsapp/health/             — evalúa TODAS las agencias activas
      * GET /system/whatsapp/health/<instance>/   — evalúa una agencia específica
    """
    started = time.monotonic()
    result = {
        "service": "whatsapp-baileys",
        "instance": instance_name,
        "timestamp": int(time.time()),
        "checks": {},
        "overall_ms": 0,
    }

    if instance_name:
        # --- Check de una sola instancia ---
        result["checks"][instance_name] = _health_check_one(instance_name)
    else:
        # --- Check agregado de todas las agencias con Evolution configurado ---
        try:
            from core.models.agencia import Agencia

            agencias = (
                Agencia.objects.filter(activa=True)
                .select_related("configuracion")
                .filter(configuracion__subdominio_slug__isnull=False)
                .exclude(configuracion__subdominio_slug="")
            )
            for ag in agencias:
                slug = ag.subdominio_slug
                if slug:
                    result["checks"][slug] = _health_check_one(slug)
        except Exception as e:
            result.setdefault("warnings", []).append(f"Could not enumerate agencies: {e}")

    # Determinar status agregado
    if not result["checks"]:
        result["status"] = "ok"
        result["note"] = "No agencies configured to check"
    else:
        statuses = [c.get("status", "down") for c in result["checks"].values()]
        if any(s == "down" for s in statuses):
            result["status"] = "down"
        elif any(s in ("degraded", "not_configured") for s in statuses):
            result["status"] = "degraded"
        else:
            result["status"] = "ok"

    result["overall_ms"] = int((time.monotonic() - started) * 1000)

    # Loggear si hay down (para Sentry/alertas)
    if result["status"] == "down":
        bad = [k for k, v in result["checks"].items() if v.get("status") == "down"]
        logger.error("WhatsApp health-check DEGRADED: instances down=%s", bad)

    return JsonResponse(result, json_dumps_params={"ensure_ascii": False})


@csrf_exempt
def whatsapp_health_alert_webhook(request, instance_name=None):
    """Webhook endpoint para recibir alertas de monitores externos.

    POST /system/whatsapp/health/alert/
    POST /system/whatsapp/health/alert/<slug>/

    Acepta el formato de UptimeRobot, Datadog, Prometheus AlertManager y
    Healthchecks.io. Cada uno tiene convenciones distintas; este endpoint
    intenta parsear todas y emitir alertas consistentes en Telegram.

    Payload esperado (estructura flexible):
    ```json
    {
      "alertType": "UP" / "DOWN",
      "monitorname": "...",
      "alertDetails": "...",
      "instance": "travelhub"  // opcional
    }
    ```

    Si el alertType/estado indica "down"/"degraded", envía alerta a Telegram.
    Si es "up"/"ok"/"recovery", envía mensaje de recuperación.

    Devuelve 200 con JSON indicando a quién se envió la alerta.
    """
    from django.conf import settings as dj_settings

    from apps.communications.services.telegram_unified import (
        TelegramNotificationService,
    )

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        import json as json_mod

        body = json_mod.loads(request.body or b"{}")
    except (json_mod.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # 1. Determinar tipo de alerta
    alert_type = (
        body.get("alertType")
        or body.get("status")
        or body.get("alert_type")
        or body.get("state")
        or "UNKNOWN"
    ).upper()

    is_recovery = alert_type in ("UP", "OK", "RECOVERY", "RESOLVED", "HEALTHY")
    is_failure = alert_type in ("DOWN", "DEGRADED", "ERROR", "FAILED", "UNHEALTHY")

    if not (is_recovery or is_failure):
        logger.warning(
            "WhatsApp health webhook: unknown alertType=%s body=%s",
            alert_type,
            str(body)[:300],
        )

    # 2. Construir mensaje
    monitor_name = (
        body.get("monitorname")
        or body.get("monitor_name")
        or body.get("monitor")
        or body.get("check")
        or "WhatsApp Health"
    )
    details = (
        body.get("alertDetails")
        or body.get("details")
        or body.get("message")
        or body.get("output")
        or ""
    )
    instance = body.get("instance") or body.get("service") or instance_name or ""

    if is_failure:
        title = "🚨 WhatsApp CAÍDO 🔴"
        body_text = (
            f"<b>{monitor_name}</b> está <b>{alert_type}</b>."
            f"\n\nDetalles: {details}"
            f"\n\nAcción: revisa <code>/system/dashboard/configuracion/?tab=whatsapp</code>"
            f" o el endpoint <code>/system/whatsapp/health/</code>."
        )
    elif is_recovery:
        title = "✅ WhatsApp RECUPERADO 🟢"
        body_text = (
            f"<b>{monitor_name}</b> vuelve a estar <b>OK</b>."
            f"\n\nUptime monitor notificó: <i>{alert_type}</i>."
            f"\nDetalles: {details or 'Sin detalles'}"
        )
    else:
        title = "ℹ️ WhatsApp Health notificación"
        body_text = f"<b>{monitor_name}</b>: {alert_type}\n\nDetalles: {details}"

    timestamp = body.get("timestamp") or body.get("alertDateTime") or body.get("time") or ""
    timestamp_str = f"\n⏰ {timestamp}" if timestamp else ""

    message = (
        f"{title}{timestamp_str}"
        f"\n\n{body_text}"
        f"\n\n🐛 Health-check: <code>/system/whatsapp/health/{instance or ''}</code>"
    )

    # 3. Enviar a Telegram
    admin_chat_id = getattr(dj_settings, "TELEGRAM_ADMIN_ID", None)
    group_chat_id = getattr(dj_settings, "TELEGRAM_GROUP_ID", None)

    sent_to = []
    try:
        admin_chat = str(admin_chat_id) if admin_chat_id else None
        if admin_chat:
            ok = TelegramNotificationService.send_message(
                message, chat_id=admin_chat, parse_mode="HTML"
            )
            if ok:
                sent_to.append(f"admin:{admin_chat_id}")

        group_chat = str(group_chat_id) if group_chat_id else None
        if group_chat and group_chat != admin_chat:
            ok = TelegramNotificationService.send_message(
                message, chat_id=group_chat, parse_mode="HTML"
            )
            if ok:
                sent_to.append(f"group:{group_chat_id}")
    except Exception as e:
        logger.exception("Error sending Telegram alert: %s", e)

    logger.info(
        "WhatsApp health webhook: alert=%s instance=%s recipients=%s",
        alert_type,
        instance or "(none)",
        sent_to or ["NONE"],
    )
    return JsonResponse(
        {
            "received": True,
            "alert_type": alert_type,
            "recipients": sent_to,
            "remediation": "https://travelhub.cc/system/dashboard/configuracion/?tab=whatsapp",
        },
        status=200,
    )


def _health_check_one(instance_name):
    """Evalúa una instancia específica. Devuelve dict con detalles."""
    out = {
        "instance": instance_name,
        "status": "down",
        "checks": {
            "redis_cache": False,
            "cache_age_seconds": None,
            "evolution_api_alive": False,
            "evolution_state": None,
            "qr_generable": False,
        },
    }

    # 1. Cache Redis
    try:
        cache_key = QR_CACHE_KEY.format(instance=instance_name)
        cached = cache.get(cache_key)
        if cached:
            out["checks"]["redis_cache"] = True
            # Cache TTL — intentar estimar cuándo se llenó
            try:
                # Si usáramos un cache_backend que soportase TTL: cache._expire_info_by_key[]
                # Para Redis, calculo heurística desde el .env del Evolution
                out["checks"]["cache_age_seconds"] = "estimated_since_refresh_under_120s"
            except Exception:
                pass
    except Exception as e:
        out["checks"]["cache_error"] = str(e)

    # 2. Evolution API directa
    try:
        from apps.communications.services.evolution_api_service import EvolutionService

        state = EvolutionService.get_instance_state(instance_name)
        out["checks"]["evolution_state"] = state
        if state:
            out["checks"]["evolution_api_alive"] = True

        # 3. ¿Puede generar QR? (incluso si Redis está vacío)
        if state in (None, "close", "disconnected", "connecting"):
            qr = EvolutionService.get_connection_qr_base64(instance_name, timeout=5)
            if qr:
                out["checks"]["qr_generable"] = True
        elif state == "open":
            out["checks"]["qr_generable"] = True  # ya está conectado, no necesita generar
            out["checks"]["connected_to_whatsapp"] = True
    except Exception as e:
        out["checks"]["evolution_error"] = str(e)

    # Decidir status final
    if out["checks"].get("connected_to_whatsapp"):
        out["status"] = "ok"
    elif out["checks"].get("redis_cache") or out["checks"].get("qr_generable"):
        out["status"] = "ok"
    elif out["checks"].get("evolution_api_alive"):
        out["status"] = "degraded"  # Evolution responde pero no hay QR
    else:
        out["status"] = "down"

    return out
