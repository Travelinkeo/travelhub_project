import hmac
import html
import json
import logging

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.finance.models import Pago

logger = logging.getLogger(__name__)


def _verify_telegram_webhook(request):
    """Verifica el origen del webhook de Telegram."""
    secret_token = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
    if secret_token:
        incoming_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not incoming_secret or not hmac.compare_digest(incoming_secret, secret_token):
            return False, "Secret token de Telegram inválido"
    return True, None


@method_decorator(csrf_exempt, name="dispatch")
class TelegramBotWebhookView(View):
    """
    🚨 CONTROL DE SEGURIDAD FISCAL | WEBHOOK TELEGRAM
    Recibe la respuesta interactiva del Staff de Finanzas para autorizar/rechazar cobros.
    Usa transacciones atómicas y select_for_update para evitar Race Conditions.
    """

    def post(self, request, *args, **kwargs):
        """post."""
        verified, error_msg = _verify_telegram_webhook(request)
        if not verified:
            logger.error(f"Webhook de Telegram rechazado: {error_msg}")
            return JsonResponse({"error": error_msg}, status=403)

        from core.api import system_context

        try:
            payload = json.loads(request.body.decode("utf-8"))
        except ValueError:
            logger.error("Payload de Telegram malformado (No es JSON válido)")
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        callback_query = payload.get("callback_query")
        if not callback_query:
            # Procesar mensajes de chat entrantes con Brain Assistant (TravelHubAgent)
            incoming_message = payload.get("message")
            if incoming_message:
                return self._handle_brain_telegram_message(incoming_message)
            return JsonResponse({"status": "ignored"})

        query_id = callback_query.get("id")
        callback_data = callback_query.get("data", "")
        message = callback_query.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")

        if not callback_data or not chat_id or not message_id or not query_id:
            logger.error("CallbackQuery de Telegram incompleto")
            return JsonResponse({"error": "Missing required callback query fields"}, status=400)

        # callback_data esperada: "pago_appr_<id_pago>" o "pago_rejh_<id_pago>"
        if not (callback_data.startswith("pago_appr_") or callback_data.startswith("pago_rejh_")):
            return JsonResponse({"status": "ignored_callback_data"})

        action = "approve" if callback_data.startswith("pago_appr_") else "reject"
        pago_id_str = callback_data.split("_")[-1]
        try:
            pago_id = int(pago_id_str)
        except ValueError:
            logger.error(f"ID de pago inválido en callback_data: {callback_data}")
            return JsonResponse({"error": "Invalid payment ID format"}, status=400)

        bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN no configurado en Django settings")
            return JsonResponse({"error": "Bot configuration missing"}, status=500)

        status_text = ""
        popup_text = ""
        message_html = ""
        success = False

        try:
            with system_context(), transaction.atomic():
                # Bloqueo de fila para evitar race conditions
                try:
                    pago = (
                        Pago.objects.select_for_update().select_related("agencia").get(pk=pago_id)
                    )
                except Pago.DoesNotExist:
                    pago = None

                if not pago:
                    status_text = "⚠️ El pago ya no existe en el sistema."
                    popup_text = "El pago ya no existe."
                    message_html = f"⚠️ <b>El pago con ID {pago_id} ya no existe o fue eliminado previamente.</b>"
                else:
                    agencia_nombre = html.escape(
                        pago.agencia.nombre.upper() if pago.agencia else "N/A"
                    )
                    monto = html.escape(f"{pago.monto_usd}")
                    ref = html.escape(pago.referencia or "Ninguna")
                    fecha_pago = html.escape(str(pago.fecha_pago))

                    if action == "approve":
                        status_text = "✅ Aprobado por Finanzas"
                        popup_text = "¡Pago aprobado con éxito!"
                        success = True
                    elif action == "reject":
                        pago.delete()
                        status_text = "❌ Rechazado y Anulado"
                        popup_text = "El pago ha sido rechazado y anulado."
                        success = True

                    message_html = (
                        f"🚨 <b>CONTROL FINANCIERO | {agencia_nombre}</b>\n"
                        f"===================================\n"
                        f"💰 <b>Pago Procesado</b>\n\n"
                        f"• <b>Monto Cobrado:</b> {monto} USD\n"
                        f"• <b>Referencia / Ref:</b> <code>{ref}</code>\n"
                        f"• <b>Fecha Registro:</b> {fecha_pago}\n"
                        f"===================================\n"
                        f"<b>Estatus:</b> {status_text}"
                    )

        except Exception as e:
            logger.exception(f"Fallo crítico procesando callback de pago {pago_id}: {str(e)}")
            self._answer_callback(bot_token, query_id, f"Error interno: {str(e)}")
            return JsonResponse({"error": "Internal database error"}, status=500)

        # Fuera de la transacción de BD hacemos los requests a Telegram
        # 1. Responder al Callback Query (quita el "loading" del botón y muestra un toast en Telegram)
        self._answer_callback(bot_token, query_id, popup_text)

        # 2. Modificar el mensaje original removiendo los botones y actualizando el texto
        self._edit_message(bot_token, chat_id, message_id, message_html)

        return JsonResponse({"status": "processed", "success": success, "action": action})

    def _answer_callback(self, bot_token, query_id, text):
        """_answer_callback."""
        from apps.common.tasks import answer_telegram_callback_task

        answer_telegram_callback_task.delay(bot_token, query_id, text)

    def _edit_message(self, bot_token, chat_id, message_id, text):
        """_edit_message."""
        from apps.common.tasks import edit_telegram_message_task

        edit_telegram_message_task.delay(bot_token, chat_id, message_id, text)

    def _handle_brain_telegram_message(self, message: dict) -> JsonResponse:
        """
        Procesa mensajes de texto entrantes de Telegram utilizando Brain Assistant (TravelHubAgent).
        """
        chat_id = message.get("chat", {}).get("id")
        user_text = message.get("text") or message.get("caption") or ""

        if not chat_id:
            return JsonResponse({"status": "ignored_no_chat_id"})

        if not user_text:
            return JsonResponse({"status": "no_text_content"})

        try:
            from apps.automation.services.ai_agent import TravelHubAgent
            from apps.common.tasks import send_telegram_task
            from core.api import agency_context
            from core.models import Agencia, AgenciaConfiguracion

            str_chat = str(chat_id)
            agencia = Agencia.objects.filter(configuracion__telegram_chat_id=str_chat).first()
            if not agencia:
                agencia = (
                    Agencia.objects.filter(nombre__icontains="Travelinkeo").first()
                    or Agencia.objects.first()
                )

            with agency_context(agencia):
                agent = TravelHubAgent(agency=agencia)
                response_text = agent.process_query(user_text)

            formatted_response = self._clean_telegram_html(response_text)

            send_telegram_task.delay(
                message=formatted_response,
                chat_id=chat_id,
                parse_mode="HTML"
            )
            return JsonResponse({"status": "processed_by_brain", "chat_id": chat_id, "agencia": agencia.nombre if agencia else None})
        except Exception as e:
            logger.error(f"Error procesando mensaje de Telegram con Brain Assistant: {e}")
            from apps.common.tasks import send_telegram_task
            send_telegram_task.delay(
                message=f"⚠️ <b>Brain Assistant:</b> Ocurrió un error al procesar tu solicitud: {html.escape(str(e))}",
                chat_id=chat_id,
                parse_mode="HTML"
            )
            return JsonResponse({"error": str(e)}, status=500)

    def _clean_telegram_html(self, text: str) -> str:
        """Limpia el texto convirtiendo markdown básico a HTML compatible con Telegram"""
        if not text:
            return ""
        import re

        clean = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
        clean = re.sub(r"\*(.*?)\*", r"<i>\1</i>", clean)
        clean = re.sub(r"`(.*?)`", r"<code>\1</code>", clean)
        return clean
