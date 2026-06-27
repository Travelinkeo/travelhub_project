import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):

    def get(self, request, *args, **kwargs):
        verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", None)
        if not verify_token:
            if not settings.DEBUG:
                return HttpResponse("Webhook not configured", status=503)
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == verify_token:
                logger.info("Webhook WA verificado exitosamente.")
                return HttpResponse(challenge, status=200)
            else:
                return HttpResponse("Token invalido", status=403)
        return HttpResponse("TravelHub WhatsApp Bot Activo", status=200)

    def _verify_signature(self, request):
        app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
        if not app_secret:
            if settings.DEBUG:
                return True
            return False

        signature = request.headers.get("X-Hub-Signature-256", "")
        if not signature:
            return False

        expected = "sha256=" + hmac.new(
            app_secret.encode("utf-8"), request.body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    def post(self, request, *args, **kwargs):
        app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
        if not app_secret and not settings.DEBUG:
            logger.error("WHATSAPP_APP_SECRET no configurado en produccion")
            return HttpResponse("Webhook not configured", status=503)

        if app_secret and not self._verify_signature(request):
            logger.warning("WhatsApp webhook: firma HMAC invalida")
            return HttpResponse(status=401)

        try:
            body = json.loads(request.body)

            if body.get("object") == "whatsapp_business_account":
                for entry in body.get("entry", []):
                    for change in entry.get("changes", []):
                        value = change.get("value", {})
                        messages = value.get("messages", [])
                        contacts = value.get("contacts", [])
                        metadata = value.get("metadata", {})

                        agencia = None
                        phone_id = metadata.get("phone_number_id")
                        if phone_id:
                            try:
                                from core.api import AgenciaConfiguracion

                                config = AgenciaConfiguracion.objects.filter(
                                    configuracion_api__contains={"WHATSAPP_PHONE_ID": phone_id}
                                ).first()
                                if config:
                                    agencia = config.agencia
                            except Exception as e_ag:
                                logger.error(f"Error resolviendo agencia por phone_id {phone_id}: {e_ag}")

                        if messages and contacts:
                            mensaje = messages[0]
                            contacto = contacts[0]

                            telefono = mensaje["from"]
                            nombre_perfil = contacto.get("profile", {}).get("name", "Cliente Nuevo")
                            telefono_limpio = telefono.replace("+", "").strip()
                            tipo_mensaje = mensaje.get("type")

                            if tipo_mensaje == "text":
                                texto = mensaje["text"]["body"]
                                logger.info(f"Mensaje WA de {nombre_perfil}: {texto}")

                                try:
                                    from apps.crm.models import Cliente, MensajeWhatsApp

                                    cliente, _ = Cliente.objects.get_or_create(
                                        telefono_principal=telefono_limpio,
                                        defaults={"nombres": nombre_perfil, "agencia": agencia},
                                    )
                                    MensajeWhatsApp.objects.create(
                                        cliente=cliente,
                                        direccion="IN",
                                        texto=texto,
                                        agencia=cliente.agencia or agencia,
                                    )
                                except Exception as e_hist:
                                    logger.error(f"Error guardando historial WA IN: {e_hist}")

                                try:
                                    from apps.crm.tasks_bot import whatsapp_ai_task

                                    whatsapp_ai_task.apply_async(
                                        args=[telefono, nombre_perfil, texto], queue="ia_fast"
                                    )
                                except Exception as e:
                                    logger.error(f"Celery no disponible, mensaje {telefono} omitido: {e}")

                            elif tipo_mensaje in ["image", "document"]:
                                media_obj = mensaje.get(tipo_mensaje)
                                media_id = media_obj.get("id")
                                mime_type = media_obj.get("mime_type")

                                logger.info(f"Documento/Imagen WA de {nombre_perfil}: id={media_id}, mime={mime_type}")

                                try:
                                    from apps.crm.models import Cliente, MensajeWhatsApp

                                    cliente, _ = Cliente.objects.get_or_create(
                                        telefono_principal=telefono_limpio,
                                        defaults={"nombres": nombre_perfil, "agencia": agencia},
                                    )
                                    MensajeWhatsApp.objects.create(
                                        cliente=cliente,
                                        direccion="IN",
                                        texto=f"[Archivo multimedia: {tipo_mensaje}]",
                                        agencia=cliente.agencia or agencia,
                                    )
                                except Exception as e_hist:
                                    logger.error(f"Error guardando historial WA IN multimedia: {e_hist}")

                                try:
                                    from apps.crm.tasks_bot import whatsapp_media_ocr_task

                                    whatsapp_media_ocr_task.apply_async(
                                        args=[
                                            telefono,
                                            nombre_perfil,
                                            media_id,
                                            mime_type,
                                            agencia.id if agencia else None,
                                        ],
                                        queue="ia_fast",
                                    )
                                except Exception as e:
                                    logger.error(f"Error al encolar whatsapp_media_ocr_task: {e}")

            return HttpResponse("EVENT_RECEIVED", status=200)

        except Exception as e:
            logger.error(f"Error procesando webhook WA: {e}")
            return HttpResponse("EVENT_RECEIVED", status=200)
