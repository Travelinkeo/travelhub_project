import hashlib
import hmac
import json
import logging

from django.conf import settings as dj_settings
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.bookings.models import BoletoImportado
from core.security import get_user_active_agency

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class ResendInboundWebhookView(View):
    """
    THE INVISIBLE AGENT
    Este webhook recibe correos de boletos, los procesa y crea ventas automáticamente.
    """

    def post(self, request, *args, **kwargs):
        # --- Signature verification ---
        resend_signing_secret = getattr(dj_settings, "RESEND_SIGNING_SECRET", "")
        if resend_signing_secret:
            signature = request.headers.get("Resend-Signature", "")
            if not signature:
                return HttpResponse("Missing signature", status=401)
            expected = hmac.new(
                resend_signing_secret.encode(), request.body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return HttpResponse("Invalid signature", status=401)
        elif not getattr(dj_settings, "DEBUG", False):
            return HttpResponse("Webhook not configured for production", status=503)
        # --- End verification ---

        try:
            data = json.loads(request.body)
            subject = data.get("subject", "Sin asunto")
            from_email = data.get("from", {}).get("email", "desconocido")
            text_body = data.get("text", "")
            html_body = data.get("html", "")

            logger.info(f"📧 Correo entrante detectado: {subject} desde {from_email}")

            # 1. CREAR REGISTRO DE IMPORTACION (Audit Point 3.2: Unificación de flujos)
            from django.core.files.base import ContentFile

            # Buscamos un usuario (consultor) por el correo de origen para asignar la agencia
            consultor = (
                User.objects.filter(email=from_email).first()
                or User.objects.filter(is_superuser=True).first()
            )
            agencia = get_user_active_agency(consultor)

            # Construir un pseudo-EML para que el servicio de extracción lo entienda mejor
            full_content = f"Subject: {subject}\nFrom: {from_email}\n\n{text_body or html_body}"

            boleto_importado = BoletoImportado.objects.create(
                agencia=agencia,
                creado_por=consultor,
                estado_parseo=BoletoImportado.EstadoParseo.PENDIENTE,
                log_parseo="Creado desde Webhook de Resend",
            )
            # Guardar el contenido como un archivo TXT para procesar
            boleto_importado.archivo_boleto.save(
                f"inbound_{boleto_importado.pk}.txt",
                ContentFile(full_content.encode("utf-8")),
                save=True,
            )

            # 2. ENCOLAR PROCESAMIENTO ASÍNCRONO
            # El pipeline completo (IA → Normalización → Venta → Factura → PDF → WhatsApp)
            # se ejecuta en segundo plano via Celery.
            from apps.bookings.tasks import parsear_boleto_individual

            parsear_boleto_individual.delay(boleto_importado.pk)
            logger.info(f"🧠 Tarea de parseo encolada para boleto {boleto_importado.pk}")

            return JsonResponse(
                {
                    "status": "accepted",
                    "message": f"Booking queued for processing: ID {boleto_importado.pk}",
                },
                status=202,
            )

        except Exception as e:
            logger.error(f"🔥 Error procesando webhook de Resend: {str(e)}")
            return HttpResponse(status=200)
