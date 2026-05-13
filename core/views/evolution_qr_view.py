import base64
import io
import json
import logging
import threading
import time

import qrcode
import requests
from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.communications.services.evolution_api_service import EvolutionService

logger = logging.getLogger(__name__)

QR_CACHE_KEY = "evo_qr:{instance}"
QR_CACHE_TTL = 120


def start_qr_fetcher(instance_name):
    """Inicia un thread en background para capturar el QR via WebSocket y cachearlo."""

    def _fetch():
        base_url = EvolutionService._get_base_url()
        headers = EvolutionService._get_headers()
        del headers["Content-Type"]

        cache_key = QR_CACHE_KEY.format(instance=instance_name)

        try:
            r = requests.get(f"{base_url}/instance/connect/{instance_name}", headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and data.get("base64"):
                    cache.set(cache_key, data["base64"], QR_CACHE_TTL)
                    return
        except Exception:
            pass

        try:
            import websocket

            ws_url = base_url.replace("http://", "ws://")
            ws_url = f"{ws_url}/{instance_name}"
            ws_headers = {"apikey": headers.get("apikey", "")}
            result = {"qr": None}

            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    event = data.get("event", "")
                    qr = data.get("qrcode", data if event else {})
                    if isinstance(qr, dict) and qr.get("base64"):
                        result["qr"] = qr["base64"]
                        ws.close()
                except Exception:
                    pass

            ws = websocket.WebSocketApp(
                ws_url,
                header=ws_headers,
                on_message=on_message,
            )
            t = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 8, "ping_timeout": 5})
            t.daemon = True
            t.start()
            time.sleep(25)
            ws.close()

            if result["qr"]:
                cache.set(cache_key, result["qr"], QR_CACHE_TTL)
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"WS QR thread error: {e}")

    t = threading.Thread(target=_fetch, daemon=True)
    t.start()


@csrf_exempt
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
        except Exception:
            pass

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
