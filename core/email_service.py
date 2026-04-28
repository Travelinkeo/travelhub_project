import os
import resend
import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# Configuración Global de Resend
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

def send_custom_email(subject, recipient, template_name, context, from_email=None):
    """
    Función centralizada que utiliza Resend para el envío de correos.
    Si no hay API Key de Resend, cae de nuevo al send_mail estándar de Django.
    """
    if not recipient:
        return False

    try:
        html_content = render_to_string(template_name, context)
        # Remitente oficial verificado
        sender = "TravelHub <notificaciones@travelhub.cc>" 

        if RESEND_API_KEY:
            # Enviar vía RESEND API (Alta entregabilidad)
            params = {
                "from": sender,
                "to": [recipient],
                "subject": subject,
                "html": html_content,
            }
            resend.Emails.send(params)
            logger.info(f"✨ Email enviado vía RESEND API: {subject} a {recipient}")
        else:
            # Fallback a Django SMTP
            text_content = strip_tags(html_content)
            send_mail(
                subject=subject,
                message=text_content,
                from_email=sender,
                recipient_list=[recipient],
                html_message=html_content,
                fail_silently=False,
            )
            logger.info(f"📧 Email enviado vía Django SMTP: {subject} a {recipient}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error crítico enviando email: {str(e)}")
        return False

def enviar_confirmacion_venta(venta):
    """Envía email de confirmación de venta al cliente"""
    if not venta.cliente or not venta.cliente.email:
        logger.warning(f"No se puede enviar confirmación para venta {venta.id_venta}: cliente sin email")
        return False
    
    return send_custom_email(
        subject=f'Confirmación de Reserva #{venta.localizador}',
        recipient=venta.cliente.email,
        template_name='core/emails/confirmacion_venta.html',
        context={
            'venta': venta,
            'cliente': venta.cliente,
            'items': venta.items_venta.all(),
        }
    )

def enviar_recordatorio_pago(venta):
    """Envía recordatorio de pago pendiente"""
    if not venta.cliente or not venta.cliente.email:
        return False
    
    return send_custom_email(
        subject=f'Recordatorio de Pago - Reserva #{venta.localizador}',
        recipient=venta.cliente.email,
        template_name='core/emails/recordatorio_pago.html',
        context={
            'venta': venta,
            'cliente': venta.cliente,
            'saldo_pendiente': venta.saldo_pendiente,
        }
    )

def enviar_cambio_estado(venta, estado_anterior):
    """Envía notificación de cambio de estado"""
    if not venta.cliente or not venta.cliente.email:
        return False
    
    return send_custom_email(
        subject=f'Actualización de Reserva #{venta.localizador}',
        recipient=venta.cliente.email,
        template_name='core/emails/cambio_estado.html',
        context={
            'venta': venta,
            'cliente': venta.cliente,
            'estado_anterior': estado_anterior,
            'estado_actual': venta.get_estado_display(),
        }
    )