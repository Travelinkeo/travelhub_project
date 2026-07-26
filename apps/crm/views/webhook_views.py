import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

ENFORCE_WEBHOOK_SECRET = True

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class WhatsAppWebhookView(View):
    """WhatsAppWebhookView."""

    def get(self, request, *args, **kwargs):
        """get."""
        verify_token = getattr(settings, "WHATSAPP_VERIFY_TOKEN", None)
        if not verify_token:
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
        """_verify_signature."""
        app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
        if not app_secret:
            return False

        signature = request.headers.get("X-Hub-Signature-256", "")
        if not signature:
            return False

        expected = (
            "sha256="
            + hmac.new(app_secret.encode("utf-8"), request.body, hashlib.sha256).hexdigest()
        )
        return hmac.compare_digest(signature, expected)

    def post(self, request, *args, **kwargs):
        """post."""
        app_secret = getattr(settings, "WHATSAPP_APP_SECRET", None)
        if not app_secret:
            logger.error("WHATSAPP_APP_SECRET no configurado")
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
                                logger.error(
                                    f"Error resolviendo agencia por phone_id {phone_id}: {e_ag}"
                                )

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
                                        args=[telefono, nombre_perfil, texto]
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Celery no disponible, mensaje {telefono} omitido: {e}"
                                    )

                            elif tipo_mensaje in ["image", "document"]:
                                media_obj = mensaje.get(tipo_mensaje)
                                media_id = media_obj.get("id")
                                mime_type = media_obj.get("mime_type")

                                logger.info(
                                    f"Documento/Imagen WA de {nombre_perfil}: id={media_id}, mime={mime_type}"
                                )

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
                                    logger.error(
                                        f"Error guardando historial WA IN multimedia: {e_hist}"
                                    )

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
                                    )
                                except Exception as e:
                                    logger.error(f"Error al encolar whatsapp_media_ocr_task: {e}")

            return HttpResponse("EVENT_RECEIVED", status=200)

        except Exception as e:
            logger.error(f"Error procesando webhook WA: {e}")
            return HttpResponse("EVENT_RECEIVED", status=200)


@method_decorator(csrf_exempt, name="dispatch")
class EvolutionWebhookView(View):
    """
    Webhook para recibir eventos de Evolution API (mensajes entrantes,
    actualizaciones de estado, delivery/read receipts).
    Evolution API POSTea aquí cuando hay eventos configurados.
    """

    def post(self, request, *args, **kwargs):
        """post."""
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return HttpResponse("Invalid JSON", status=400)

        event_type = body.get("event", "")
        instance = body.get("instance", "")
        data = body.get("data", {})

        logger.info(f"Evolution webhook: event={event_type}, instance={instance}")

        if event_type == "MESSAGES_UPSERT":
            self._handle_message_upsert(instance, data)
        elif event_type == "MESSAGES_UPDATE":
            self._handle_message_update(instance, data)
        elif event_type == "SEND_MESSAGE":
            self._handle_send_result(instance, data)
        elif event_type == "CONNECTION_UPDATE":
            self._handle_connection_update(instance, data)
        else:
            logger.debug(f"Evolution webhook: evento no manejado {event_type}")

        return HttpResponse("OK", status=200)

    def _find_agencia_by_instance(self, instance_name: str):
        """_find_agencia_by_instance."""
        try:
            from core.models import AgenciaConfiguracion

            config = AgenciaConfiguracion.objects.filter(
                evolution_instance_name=instance_name
            ).first()
            if config:
                return config.agencia
        except Exception as e:
            logger.warning(f"Error buscando agencia por instancia {instance_name}: {e}")
        return None

    def _handle_message_upsert(self, instance: str, data: dict):
        """Procesa mensajes entrantes desde Evolution API."""
        key = data.get("key", {})
        message = data.get("message", {})
        push_name = data.get("pushName", "Cliente")
        remote_jid = key.get("remoteJid", "")
        from_me = key.get("fromMe", False)
        message_id = key.get("id", "")

        if from_me:
            return

        telefono = remote_jid.split("@")[0]
        tipo = message.get("messageType", "")

        agencia = self._find_agencia_by_instance(instance)

        try:
            from apps.crm.models import Cliente, MensajeWhatsApp

            cliente, _ = Cliente.objects.get_or_create(
                telefono_principal=telefono,
                defaults={"nombres": push_name, "agencia": agencia},
            )

            if tipo == "conversation":
                texto = message.get("conversation", "")
            elif tipo == "imageMessage":
                texto = "[Imagen recibida]"
            elif tipo == "documentMessage":
                texto = "[Documento recibido]"
            elif tipo == "locationMessage":
                texto = "[Ubicación recibida]"
            elif tipo == "buttonsResponseMessage":
                texto = message.get("buttonsResponseMessage", {}).get("text", "")
            elif tipo == "listResponseMessage":
                texto = message.get("listResponseMessage", {}).get("text", "")
            else:
                texto = f"[{tipo}]"

            MensajeWhatsApp.objects.create(
                cliente=cliente,
                direccion="IN",
                texto=texto,
                message_id=message_id,
                estado="delivered",
                agencia=cliente.agencia or agencia,
            )

            try:
                from apps.crm.tasks_bot import whatsapp_ai_task

                whatsapp_ai_task.apply_async(args=[telefono, push_name, texto])
            except Exception as e:
                logger.error(f"Error encolando IA para Evolution inbound: {e}")

        except Exception as e:
            logger.error(f"Error procesando mensaje Evolution entrante: {e}")

    def _handle_message_update(self, instance: str, data: dict):
        """Procesa actualizaciones de estado (entregado/leído)."""
        key = data.get("key", {})
        message_id = key.get("id", "")
        status = data.get("status", "")

        status_map = {
            "PENDING": "pending",
            "SERVER_ACK": "sent",
            "DELIVERY_ACK": "delivered",
            "READ": "read",
            "PLAYED": "read",
            "ERROR": "failed",
        }

        nuevo_estado = status_map.get(status, "pending")

        try:
            from apps.crm.models import MensajeWhatsApp

            actualizados = MensajeWhatsApp.objects.filter(message_id=message_id).update(
                estado=nuevo_estado
            )
            if actualizados:
                logger.info(f"Mensaje {message_id} actualizado a estado '{nuevo_estado}'")
        except Exception as e:
            logger.error(f"Error actualizando estado mensaje {message_id}: {e}")

    def _handle_send_result(self, instance: str, data: dict):
        """Procesa resultado de envío (éxito/fallo) y guarda el message_id."""
        key = data.get("key", {})
        message_id = key.get("id", "")
        status = data.get("status", "")

        if not message_id:
            return

        nuevo_estado = "sent" if status != "ERROR" else "failed"

        try:
            from apps.crm.models import MensajeWhatsApp

            MensajeWhatsApp.objects.filter(message_id="").exclude(texto__exact="").order_by(
                "-timestamp"
            )[:1].update(message_id=message_id, estado=nuevo_estado)
        except Exception as e:
            logger.error(f"Error guardando message_id {message_id}: {e}")

    def _handle_connection_update(self, instance: str, data: dict):
        """Procesa cambios en el estado de conexión de la instancia."""
        state = data.get("state", "")
        logger.info(f"Evolution instance '{instance}' connection state: {state}")
