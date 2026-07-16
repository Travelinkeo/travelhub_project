import logging

logger = logging.getLogger(__name__)


class FacturaService:
    """
    Service layer to explicitly orchestrate operations on Factura,
    completely decoupled from implicit signals.
    """

    @staticmethod
    def capture_previous_pdf(factura):
        return False

    @staticmethod
    def send_to_telegram_if_needed(factura):
        try:
            from apps.communications.services.telegram_unified import (
                TelegramNotificationService,
            )

            cliente_nombre = factura.cliente.get_nombre_completo() if factura.cliente else "N/A"
            caption = (
                f"🧾 <b>Nueva Factura Generada</b>\n"
                f"🔢 Nro: {factura.numero_control}\n"
                f"👤 Cliente: {cliente_nombre}\n"
                f"💰 Total: {factura.gran_total_usd:,.2f} USD\n"
                f"📅 Fecha: {factura.fecha_emision}"
            )

            TelegramNotificationService.send_document(file_path=None, caption=caption)
            logger.info(
                f"📲 Factura {factura.numero_control} notificada a Telegram vía FacturaService."
            )
            return True
        except Exception as e:
            logger.error(f"Error in FacturaService.send_to_telegram_if_needed: {e}")
        return False

    @staticmethod
    def send_to_whatsapp_if_needed(factura):
        from django.conf import settings

        cliente = factura.cliente
        if not cliente or not cliente.telefono_principal:
            logger.info(
                f"Invoice WhatsApp: Factura {factura.numero_control} sin cliente o sin teléfono."
            )
            return False

        is_enabled = getattr(settings, "WHATSAPP_NOTIFICATIONS_ENABLED", False)
        if not is_enabled:
            logger.info("Invoice WhatsApp: Notificaciones por WhatsApp desactivadas.")
            return False

        agencia = factura.agencia
        agencia_nombre = agencia.nombre if agencia else "TravelHub"

        mensaje = (
            f"🧾 *Nueva Factura Generada - {agencia_nombre}*\n\n"
            f"Estimado/a *{cliente.get_nombre_completo()}*,\n\n"
            f"Te informamos que se ha emitido tu factura.\n\n"
            f"📋 *Detalles:*\n"
            f"• Factura Nro: *{factura.numero_control}*\n"
            f"• Total: *{factura.gran_total_usd:,.2f} USD*\n"
            f"• Fecha de Emisión: {factura.fecha_emision}\n\n"
            f"¡Gracias por tu preferencia!\n"
            f"_{agencia_nombre}_"
        )

        try:
            from django.db import transaction

            from core.api import enviar_notificacion_whatsapp_task

            transaction.on_commit(
                lambda: enviar_notificacion_whatsapp_task.delay(
                    numero_cliente=cliente.telefono_principal,
                    mensaje=mensaje,
                    email_cliente=cliente.email,
                    agencia_id=agencia.id if agencia else None,
                    media_url=None,
                    file_name=f"Factura_{factura.numero_control}.pdf",
                )
            )
            logger.info(
                f"📲 Factura {factura.numero_control} encolada a WhatsApp vía FacturaService."
            )
            return True
        except Exception as e_celery:
            logger.error(f"Error encolando tarea de WhatsApp para factura: {e_celery}")
        return False
