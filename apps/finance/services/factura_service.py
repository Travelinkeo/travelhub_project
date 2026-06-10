import logging

from apps.finance.models import Factura

logger = logging.getLogger(__name__)


class FacturaService:
    """
    Service layer to explicitly orchestrate operations on Factura,
    completely decoupled from implicit signals.
    """

    @staticmethod
    def capture_previous_pdf(factura):
        """
        Detects if the PDF file changed by saving the old PDF path in a temporary attribute.
        """
        if factura.pk:
            try:
                old_inst = Factura.objects.get(pk=factura.pk)
                factura._old_pdf = old_inst.archivo_pdf
                return True
            except Factura.DoesNotExist:
                factura._old_pdf = None
        else:
            factura._old_pdf = None
        return False

    @staticmethod
    def send_to_telegram_if_needed(factura):
        """
        Sends the invoice document via Telegram if a new PDF has been generated/uploaded.
        """
        nuevo_pdf = bool(factura.archivo_pdf)
        viejo_pdf = bool(getattr(factura, "_old_pdf", None))
        cambio_pdf = nuevo_pdf and (not viejo_pdf or factura.archivo_pdf != factura._old_pdf)

        if cambio_pdf:
            try:
                from apps.communications.services.telegram_unified import (
                    TelegramNotificationService,
                )

                simbolo = factura.moneda.simbolo if factura.moneda else "$"
                caption = (
                    f"🧾 <b>Nueva Factura Generada</b>\n"
                    f"🔢 Nro: {factura.numero_factura}\n"
                    f"👤 Cliente: {factura.cliente_nombre or 'N/A'}\n"
                    f"💰 Total: {factura.monto_total:,.2f} {simbolo}\n"
                    f"📅 Fecha: {factura.fecha_emision}"
                )

                pdf_path_or_url = None
                try:
                    # Intento 1: Path local
                    if hasattr(factura.archivo_pdf, "path"):
                        pdf_path_or_url = factura.archivo_pdf.path
                except NotImplementedError:
                    # Intento 2: URL remota
                    if hasattr(factura.archivo_pdf, "url"):
                        pdf_path_or_url = factura.archivo_pdf.url

                if pdf_path_or_url:
                    TelegramNotificationService.send_document(
                        file_path=pdf_path_or_url, caption=caption
                    )
                    logger.info(
                        f"📲 Factura {factura.numero_factura} enviada a Telegram vía FacturaService."
                    )
                    return True
                else:
                    logger.error(
                        f"❌ FacturaService: No se pudo obtener Path ni URL de Factura {factura.numero_factura}"
                    )
            except Exception as e:
                logger.error(f"Error in FacturaService.send_to_telegram_if_needed: {e}")
        return False

    @staticmethod
    def send_to_whatsapp_if_needed(factura):
        """
        Sends the invoice document via WhatsApp to the client if a new PDF has been generated/uploaded.
        """
        from django.conf import settings

        nuevo_pdf = bool(factura.archivo_pdf)
        viejo_pdf = bool(getattr(factura, "_old_pdf", None))
        cambio_pdf = nuevo_pdf and (not viejo_pdf or factura.archivo_pdf != factura._old_pdf)

        if cambio_pdf:
            cliente = factura.cliente
            if not cliente or not cliente.telefono_principal:
                logger.info(
                    f"Invoice WhatsApp: Factura {factura.numero_factura} sin cliente o sin teléfono."
                )
                return False

            is_enabled = getattr(settings, "WHATSAPP_NOTIFICATIONS_ENABLED", False)
            if not is_enabled:
                logger.info("Invoice WhatsApp: Notificaciones por WhatsApp desactivadas.")
                return False

            agencia = factura.agencia
            agencia_nombre = agencia.nombre if agencia else "TravelHub"
            simbolo = factura.moneda.simbolo if factura.moneda else "$"

            mensaje = (
                f"🧾 *Nueva Factura Generada - {agencia_nombre}*\n\n"
                f"Estimado/a *{factura.cliente_nombre or cliente.get_nombre_completo()}*,\n\n"
                f"Te informamos que se ha emitido tu factura.\n\n"
                f"📋 *Detalles:*\n"
                f"• Factura Nro: *{factura.numero_factura}*\n"
                f"• Total: *{factura.monto_total:,.2f} {simbolo}*\n"
                f"• Fecha de Emisión: {factura.fecha_emision}\n\n"
                f"Adjunto encontrarás tu factura en formato PDF.\n\n"
                f"¡Gracias por tu preferencia!\n"
                f"_{agencia_nombre}_"
            )

            pdf_url = ""
            try:
                if factura.archivo_pdf:
                    try:
                        pdf_url = factura.archivo_pdf.url
                    except Exception:
                        pdf_url = f"{settings.MEDIA_URL if 'http' in settings.MEDIA_URL else 'https://travelhub.travelinkeo.com' + settings.MEDIA_URL}{factura.archivo_pdf.name}"

                    if pdf_url and not pdf_url.startswith("http"):
                        pdf_url = f"https://travelhub.travelinkeo.com{pdf_url}"
            except Exception as e:
                logger.error(f"Error generando URL del PDF de factura para WhatsApp: {e}")

            try:
                from django.db import transaction

                from core.api import enviar_notificacion_whatsapp_task

                transaction.on_commit(
                    lambda: enviar_notificacion_whatsapp_task.delay(
                        numero_cliente=cliente.telefono_principal,
                        mensaje=mensaje,
                        email_cliente=cliente.email,
                        agencia_id=agencia.id if agencia else None,
                        media_url=pdf_url if pdf_url else None,
                        file_name=f"Factura_{factura.numero_factura}.pdf",
                    )
                )
                logger.info(
                    f"📲 Factura {factura.numero_factura} encolada a WhatsApp vía FacturaService."
                )
                return True
            except Exception as e_celery:
                logger.error(f"Error encolando tarea de WhatsApp para factura: {e_celery}")
        return False
