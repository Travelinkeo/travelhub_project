"""Módulo views whatsapp de la aplicación cotizaciones.
"""

import hashlib
import hmac
import logging
from urllib.parse import parse_qs

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class IncomingWhatsAppWebhook:
    """Clase IncomingWhatsAppWebhook. Uso: según contexto de la aplicación.
    """
    def _verify_signature(self, request):
        # _verify_signature:  verify signature. Args: según implementación. Returns: según implementación.
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        if not auth_token:
            return False

        signature = request.headers.get("X-Twilio-Signature", "")
        if not signature:
            return False

        url = request.build_absolute_uri()
        if request.method == "POST":
            params = dict(parse_qs(request.body.decode("utf-8"), keep_blank_values=True))
            params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
        else:
            params = {}

        expected = hmac.new(
            auth_token.encode("utf-8"),
            (url + "".join(sorted(params.items()))).encode("utf-8"),
            hashlib.sha1,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def post(self, request, *args, **kwargs):
        # post: Post. Args: según implementación. Returns: según implementación.
        auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        if not auth_token:
            logger.error("TWILIO_AUTH_TOKEN no configurado")
            return HttpResponse("Webhook not configured", status=503)

        if auth_token and not self._verify_signature(request):
            logger.warning("Twilio webhook: firma HMAC invalida")
            return HttpResponse(status=401)

        try:
            sender_id = request.POST.get("From", "")
            body_text = request.POST.get("Body", "").strip()
            num_media = int(request.POST.get("NumMedia", 0))

            if not sender_id:
                return HttpResponse("Invalid request format.", status=400)

            raw_phone = sender_id.replace("whatsapp:", "")
            logger.info(f"[Webhook Incoming] Mensaje recibido de {raw_phone}. Media={num_media}")

            media_url = ""
            media_type = ""
            if num_media > 0:
                media_type = request.POST.get("MediaContentType0", "")
                media_url = request.POST.get("MediaUrl0", "")

            from apps.common.tasks import process_twilio_voice_quote_task

            process_twilio_voice_quote_task.delay(
                sender_id=sender_id,
                raw_phone=raw_phone,
                body_text=body_text,
                num_media=num_media,
                media_url=media_url,
                media_type=media_type,
            )

            response_twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
            return HttpResponse(response_twiml, content_type="text/xml", status=200)

        except Exception as e:
            logger.error(f"Error procesando webhook Twilio: {e}")
            response_twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
            return HttpResponse(response_twiml, content_type="text/xml", status=200)
