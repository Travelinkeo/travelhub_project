import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.core.cache import cache
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

    Autenticación: Requiere header 'apikey' con el mismo token configurado
    en WHATSAPP_MICROSERVICE_TOKEN.
    """

    def _verify_auth(self, request) -> bool:
        """Verifica que el webhook venga de Evolution API."""
        expected = getattr(settings, "WHATSAPP_MICROSERVICE_TOKEN", None)
        if not expected:
            logger.warning(
                "WHATSAPP_MICROSERVICE_TOKEN no configurado — webhook Evolution sin auth"
            )
            return True
        received = request.headers.get("apikey", "")
        return received == expected

    def post(self, request, *args, **kwargs):
        """post."""
        if not self._verify_auth(request):
            logger.warning("Evolution webhook: apikey invalida")
            return HttpResponse(status=401)

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
        elif event_type == "QRCODE_UPDATED":
            self._handle_qrcode_updated(instance, data)
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

            MensajeWhatsApp.objects.filter(message_id=message_id).update(estado=nuevo_estado)
        except Exception as e:
            logger.error(f"Error actualizando message_id {message_id}: {e}")

    def _handle_connection_update(self, instance: str, data: dict):
        """Procesa cambios en el estado de conexión de la instancia."""
        state = data.get("state", "")
        logger.info(f"Evolution instance '{instance}' connection state: {state}")
        if state == "open":
            try:
                cache.delete(f"evo_qr:{instance}")
            except Exception as e:
                logger.warning(f"Error limpiando cache QR para instancia {instance}: {e}")

    def _handle_qrcode_updated(self, instance: str, data: dict):
        """Procesa evento QRCODE_UPDATED de Evolution API y cachea el QR en Redis."""
        logger.info(f"Evolution QRCODE_UPDATED for instance '{instance}'")
        qr_b64 = None
        if isinstance(data, dict):
            qrcode_data = data.get("qrcode", data)
            if isinstance(qrcode_data, dict):
                qr_b64 = qrcode_data.get("base64")
                if not qr_b64:
                    qr_b64 = qrcode_data.get("code")
            else:
                qr_b64 = data.get("base64") or data.get("code")
        if qr_b64:
            try:
                cache.set(f"evo_qr:{instance}", qr_b64, 300)
                logger.info(f"QR cacheado en Redis para instancia '{instance}' via webhook")
            except Exception as e:
                logger.error(f"Error cacheando QR en Redis: {e}")
        else:
            logger.warning(f"QRCODE_UPDATED sin base64 para '{instance}': {data}")


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(View):
    """
    Webhook unificado para recibir Updates de Telegram (Bot de Agencia o Plataforma).
    Maneja el comando Deep Linking `/start cli_<uuid>` para autoinscribir pasajeros.
    """

    def post(self, request, agencia_id: int = None, *args, **kwargs):
        """Procesa peticiones POST de Telegram Bot Webhook."""
        try:
            body = json.loads(request.body)

            # --- MANEJO DE BOTONES INLINE (CALLBACK QUERY) ---
            callback_query = body.get("callback_query")
            if callback_query:
                self._handle_callback_query(callback_query, agencia_id)
                return HttpResponse("OK", status=200)

            # --- MANEJO DE MENSAJES Y COMANDOS SLASH ---
            message = body.get("message") or body.get("edited_message")
            if not message:
                return HttpResponse("OK", status=200)

            text = message.get("text", "").strip()
            chat = message.get("chat", {})
            chat_id = str(chat.get("id", ""))
            from_user = message.get("from", {})

            if text.startswith("/start"):
                self._handle_start_command(text, chat_id, from_user, agencia_id)
            elif text.startswith("/pnr"):
                self._handle_pnr_command(text, chat_id, agencia_id)
            elif text.startswith("/ventas"):
                self._handle_ventas_command(chat_id, agencia_id)
            elif text.startswith("/whatsapp"):
                self._handle_whatsapp_command(chat_id, agencia_id)
            elif text.startswith("/cliente"):
                self._handle_cliente_command(text, chat_id, agencia_id)

            return HttpResponse("OK", status=200)
        except Exception as e:
            logger.error(f"[TelegramWebhook] Error procesando webhook: {e}")
            return HttpResponse("OK", status=200)

    def _handle_start_command(
        self, text: str, chat_id: str, from_user: dict, agencia_id: int = None
    ):
        """Procesa comando /start y payload de autoinscripción."""
        from django.utils import timezone

        from apps.communications.services.telegram_unified import TelegramNotificationService
        from apps.crm.models import Cliente
        from core.models import Agencia

        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""

        agencia = None
        if agencia_id:
            agencia = Agencia.objects.filter(pk=agencia_id).first()

        cliente = None
        if payload.startswith("cli_"):
            client_uuid = payload[4:]
            try:
                cliente = Cliente.objects.get(uuid=client_uuid)
                if not agencia and hasattr(cliente, "agencia"):
                    agencia = cliente.agencia
            except (Cliente.DoesNotExist, ValueError):
                logger.warning(f"[TelegramWebhook] Cliente no encontrado con UUID {client_uuid}")
                cliente = None

        if cliente:
            cliente.telegram_chat_id = chat_id
            cliente.telegram_subscribed_at = timezone.now()
            cliente.preferred_channel = Cliente.PreferredChannel.TELEGRAM
            cliente.save(
                update_fields=["telegram_chat_id", "telegram_subscribed_at", "preferred_channel"]
            )

            agencia_nombre = agencia.nombre if agencia else "tu agencia de viajes"
            welcome_msg = (
                f"🎉 <b>¡Hola {cliente.nombres}!</b>\n\n"
                f"Tu cuenta ha sido vinculada exitosamente con <b>{agencia_nombre}</b>.\n\n"
                f"✈️ A partir de este momento recibirás en este chat tus pases de abordar, "
                f"confirmaciones de reserva y notificaciones de vuelo en tiempo real."
            )
            TelegramNotificationService.send_message(welcome_msg, chat_id=chat_id, agencia=agencia)
            logger.info(
                f"[TelegramWebhook] Cliente {cliente.id} ({cliente.nombres}) vinculado a Telegram (chat_id: {chat_id})"
            )
        else:
            # Comando /start sin payload específico
            msg = (
                "👋 <b>¡Bienvenido a nuestro Bot de Notificaciones!</b>\n\n"
                "Para vincular tu cuenta y recibir tus pases de abordar, por favor usa el enlace "
                "de activación enviado por tu agencia de viajes."
            )
            TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)

    def _handle_pnr_command(self, text: str, chat_id: str, agencia_id: int = None):
        """Procesa comando /pnr <localizador> consultando boletos e itinerarios."""
        from apps.communications.services.booking_queries_service import BookingQueriesService
        from apps.communications.services.telegram_unified import TelegramNotificationService
        from core.models import Agencia

        agencia = Agencia.objects.filter(pk=agencia_id).first() if agencia_id else None
        parts = text.split(maxsplit=1)
        pnr = parts[1].strip().upper() if len(parts) > 1 else ""

        if not pnr:
            msg = "⚠️ Por favor especifica el PNR/localizador. Ejemplo: <code>/pnr WPYVSD</code>"
            TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)
            return

        boleto = BookingQueriesService.buscar_boleto_por_pnr(pnr, agencia_id=agencia_id)

        if not boleto:
            msg = f"❌ No se encontró ningún boleto cargado con el localizador <b>{pnr}</b>."
            TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)
            return

        msg = (
            f"✈️ <b>INFORMACIÓN DE RESERVA #{boleto.localizador}</b>\n\n"
            f"👤 <b>Pasajero:</b> {boleto.pasajero_nombre_completo or 'N/A'}\n"
            f"🆔 <b>ID Pasajero:</b> {boleto.pasajero_id or 'N/A'}\n"
            f"✈️ <b>Aerolínea:</b> {boleto.aerolinea or 'N/A'}\n"
            f"📍 <b>Ruta:</b> {boleto.origen or '?'} ➔ {boleto.destino or '?'}\n"
            f"📅 <b>Fecha Salida:</b> {boleto.fecha_salida or 'N/A'}\n"
            f"📊 <b>Estado Parseo:</b> {boleto.estado_parseo.upper()}"
        )

        buttons = [
            [
                {
                    "text": "🌐 Ver en TravelHub",
                    "url": f"https://travelhub.cc/erp/boletos-importados/{boleto.id}/",
                }
            ]
        ]
        keyboard = TelegramNotificationService.build_inline_keyboard(buttons)
        TelegramNotificationService.send_message(
            msg, chat_id=chat_id, agencia=agencia, reply_markup=keyboard
        )

    def _handle_ventas_command(self, chat_id: str, agencia_id: int = None):
        """Procesa comando /ventas mostrando un resumen express de ventas de hoy."""
        from django.utils import timezone

        from apps.communications.services.booking_queries_service import BookingQueriesService
        from apps.communications.services.telegram_unified import TelegramNotificationService
        from core.models import Agencia

        agencia = Agencia.objects.filter(pk=agencia_id).first() if agencia_id else None
        today = timezone.now().date()

        resumen = BookingQueriesService.resumen_ventas_del_dia(today, agencia_id=agencia_id)

        msg = (
            f"📊 <b>RESUMEN DE VENTAS DE HOY ({today.strftime('%d/%m/%Y')})</b>\n\n"
            f"📈 <b>Ventas Emitidas:</b> {resumen['total']}\n"
            f"💰 <b>Monto Total:</b> ${resumen['monto_total']:,.2f} USD\n\n"
            f"<i>Reporte generado automáticamente vía TravelHub Bot.</i>"
        )
        TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)

    def _handle_whatsapp_command(self, chat_id: str, agencia_id: int = None):
        """Procesa comando /whatsapp verificando la salud de la instancia de WhatsApp."""
        from apps.communications.services.evolution_api_service import EvolutionService
        from apps.communications.services.telegram_unified import TelegramNotificationService
        from core.models import Agencia

        agencia = Agencia.objects.filter(pk=agencia_id).first() if agencia_id else None
        instance_name = f"agencia_{agencia_id}" if agencia_id else "instancia_principal"

        if agencia and hasattr(agencia, "configuracion") and agencia.configuracion:
            instance_name = getattr(agencia.configuracion, "evolution_instance_name", instance_name)

        state = EvolutionService.get_instance_state(instance_name)
        status_icon = "🟢" if state == "open" else "🔴"

        msg = (
            f"📱 <b>ESTADO DE WHATSAPP - INSTANCIA '{instance_name}'</b>\n\n"
            f"Estado: {status_icon} <b>{state.upper()}</b>\n\n"
        )

        buttons = []
        if state != "open":
            msg += "⚠️ Tu línea de WhatsApp se encuentra desconectada. Haz clic en el botón de abajo para reconectar."
            buttons.append(
                [
                    {
                        "text": "📲 Escanear Código QR",
                        "url": f"https://travelhub.cc/manager/qr/{instance_name}/",
                    }
                ]
            )

        keyboard = TelegramNotificationService.build_inline_keyboard(buttons) if buttons else None
        TelegramNotificationService.send_message(
            msg, chat_id=chat_id, agencia=agencia, reply_markup=keyboard
        )

    def _handle_cliente_command(self, text: str, chat_id: str, agencia_id: int = None):
        """Procesa comando /cliente <busqueda> consultando la base de clientes."""
        from django.db.models import Q

        from apps.communications.services.telegram_unified import TelegramNotificationService
        from apps.crm.models import Cliente
        from core.models import Agencia

        agencia = Agencia.objects.filter(pk=agencia_id).first() if agencia_id else None
        parts = text.split(maxsplit=1)
        query = parts[1].strip() if len(parts) > 1 else ""

        if not query:
            msg = "⚠️ Especifica un término de búsqueda. Ejemplo: <code>/cliente Mauricio</code>"
            TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)
            return

        qs = Cliente.objects.filter(
            Q(nombres__icontains=query) | Q(apellidos__icontains=query) | Q(email__icontains=query)
        )
        if agencia_id:
            qs = qs.filter(agencia_id=agencia_id)

        clientes = qs[:3]
        if not clientes:
            msg = f"❌ No se encontraron clientes con el término <b>{query}</b>."
            TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)
            return

        msg_lines = [f"👤 <b>RESULTADOS DE BÚSQUEDA ('{query}')</b>\n"]
        for c in clientes:
            msg_lines.append(
                f"• <b>{c.nombres} {c.apellidos or ''}</b>\n"
                f"  📧 {c.email or 'Sin email'} | 📞 {c.telefono_principal or 'Sin teléfono'}\n"
                f"  Canal Preferido: <b>{c.preferred_channel.upper()}</b>"
            )

        TelegramNotificationService.send_message(
            "\n".join(msg_lines), chat_id=chat_id, agencia=agencia
        )

    def _handle_callback_query(self, callback_query: dict, agencia_id: int = None):
        """Maneja las interacciones de botones Inline (callback_query)."""
        from apps.communications.services.telegram_unified import TelegramNotificationService
        from core.models import Agencia

        callback_id = callback_query.get("id")
        data = callback_query.get("data", "")
        chat_id = str(callback_query.get("message", {}).get("chat", {}).get("id", ""))
        agencia = Agencia.objects.filter(pk=agencia_id).first() if agencia_id else None

        if data.startswith("approve_"):
            item_id = data.split("_")[1]
            TelegramNotificationService.answer_callback_query(
                callback_id, text="✅ Excepción Aprobada", agencia=agencia
            )
            msg = f"✅ Excepción para el ítem #{item_id} aprobada exitosamente por el staff."
            TelegramNotificationService.send_message(msg, chat_id=chat_id, agencia=agencia)
        else:
            TelegramNotificationService.answer_callback_query(
                callback_id, text="Acción recibida", agencia=agencia
            )
