import logging

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class IncomingWhatsAppWebhook(View):
    """
    Receptor asíncrono de mensajes entrantes de WhatsApp desde Twilio.
    Delega todo el procesamiento pesado a una Celery task.
    """

    def post(self, request, *args, **kwargs):
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
