import logging
import os

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def send_ticket_to_client(venta_id, pdf_content, filename="boleto.pdf"):
    """
    Envía el boleto procesado al cliente final.
    Adjunta el PDF generado.
    """
    from django.apps import apps

    Venta = apps.get_model("bookings", "Venta")
    try:
        venta = Venta.objects.select_related("cliente", "agencia").get(pk=venta_id)
        cliente = venta.cliente
        agencia = venta.agencia

        if not cliente or not cliente.email:
            logger.warning(f"No se puede enviar boleto para venta {venta_id}: Cliente sin email.")
            return False

        subject = f"✈️ Tu Boleto está listo - Localizador {venta.localizador}"

        # Determinar remitente (Agencia o Default)
        from_email = (
            getattr(agencia, "email_ventas", None)
            or getattr(agencia, "email_principal", None)
            or settings.DEFAULT_FROM_EMAIL
        )

        # Si usamos Resend directo vía API (como en email_unified)
        import resend

        resend_api_key = os.environ.get("RESEND_API_KEY")

        if resend_api_key:
            resend.api_key = resend_api_key

            # Preparar parámetros para Resend
            # Nota: Resend soporta adjuntos en su API
            params = {
                "from": f"{agencia.nombre if agencia else 'TravelHub'} <{from_email}>",
                "to": [cliente.email],
                "subject": subject,
                "html": f"<h2>¡Hola {cliente.get_nombre_completo()}!</h2><p>Adjunto encontrarás tu boleto electrónico para el localizador <b>{venta.localizador}</b>.</p><p>¡Buen viaje!</p>",
                "attachments": [
                    {
                        "filename": filename,
                        "content": list(pdf_content)
                        if isinstance(pdf_content, bytes)
                        else pdf_content,
                    }
                ],
            }
            resend.Emails.send(params)
            logger.info(f" Boleto enviado vía Resend API a {cliente.email}")
        else:
            # Fallback a Django SMTP (que también puede estar configurado con Resend)
            email_msg = EmailMessage(
                subject=subject,
                body=f"Hola {cliente.get_nombre_completo()},\n\nAdjunto encontrarás tu boleto electrónico.\n\n¡Buen viaje!",
                from_email=from_email,
                to=[cliente.email],
            )
            email_msg.attach(filename, pdf_content, "application/pdf")
            email_msg.send(fail_silently=False)
            logger.info(f" Boleto enviado vía Django SMTP a {cliente.email}")

        return True

    except Venta.DoesNotExist:
        logger.error(f"Venta {venta_id} no encontrada para envío de boleto.")
        return False
    except Exception as e:
        logger.exception(f"Error enviando boleto al cliente: {e}")
        return False
