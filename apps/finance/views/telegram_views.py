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
    """Verifica que el webhook provenga de Telegram validando el secret_token.

    Telegram soporta la verificación via X-Telegram-Bot-Api-Secret-Token header
    configurado al momento de setWebhook. Por seguridad (fail-closed), si no hay
    secret configurado el webhook se RECHAZA: el token del bot puede estar
    filtrado (visto en .env.commits) y no basta para autenticar el origen.

    Para habilitar el webhook, definir en settings/entorno:
        TELEGRAM_WEBHOOK_SECRET=<string_aleatorio_largo>
    Y establecerlo al hacer `setWebhook` contra la API de Telegram.
    """
    secret_token = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", None)
    if not secret_token:
        logger.error(
            "Webhook de Telegram rechazado: TELEGRAM_WEBHOOK_SECRET no configurado. "
            "El webhook no puede autenticar el origen sin secret token (fail-closed)."
        )
        return False, "TELEGRAM_WEBHOOK_SECRET no configurado (fail-closed)"

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
            # Es una actualización normal de Telegram (no callback_query), la ignoramos de forma exitosa
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
