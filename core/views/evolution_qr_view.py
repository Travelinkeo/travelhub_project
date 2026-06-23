import base64
import binascii
import io
import logging

import qrcode
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

QR_CACHE_KEY = "evo_qr:{instance}"
QR_CACHE_TTL = 300  # 5 minutos — Celery Beat lo renueva cada 90s


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
