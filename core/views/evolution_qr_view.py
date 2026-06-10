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
QR_CACHE_TTL = 120


def start_qr_fetcher(instance_name):
    """Encola una Celery task para capturar el QR de Evolution y cachearlo."""
    from apps.common.tasks import fetch_evolution_qr_task

    fetch_evolution_qr_task.delay(instance_name)


@csrf_exempt
@login_required
def evolution_qr_proxy(request, instance_name):
    """Sirve el QR como PNG (cache Redis, placeholder mientras carga)."""
    cache_key = QR_CACHE_KEY.format(instance=instance_name)
    cached = cache.get(cache_key)

    if cached:
        try:
            img_data = base64.b64decode(cached)
            resp = HttpResponse(img_data, content_type="image/png")
            resp["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return resp
        except (binascii.Error, ValueError) as e:
            logger.debug("Invalid cached base64 for %s: %s", instance_name, e)

    start_qr_fetcher(instance_name)

    buf = io.BytesIO()
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(f"evolution:{instance_name}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="#3b82f6", back_color="white")
    img.save(buf, format="PNG")
    resp = HttpResponse(buf.getvalue(), content_type="image/png")
    resp["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp
