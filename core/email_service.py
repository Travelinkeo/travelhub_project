"""
Servicio de emails automáticos para TravelHub
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)


def enviar_confirmacion_venta(venta):
    """Envía email de confirmación de venta al cliente"""
    if not venta.cliente or not venta.cliente.email:
        logger.warning(f"No se puede enviar confirmación para venta {venta.id_venta}: cliente sin email")
        return False
    
    try:
        # Renderizar template HTML
        html_content = render_to_string('core/emails/confirmacion_venta.html', {
            'venta': venta,
            'cliente': venta.cliente,
            'items': venta.items_venta.all(),
        })
        
        # Versión texto plano
        text_content = strip_tags(html_content)
        
        # Enviar email
        send_mail(
            subject=f'Confirmación de Reserva #{venta.localizador}',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[venta.cliente.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"Email de confirmación enviado para venta {venta.id_venta}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando confirmación venta {venta.id_venta}: {str(e)}")
        return False


def enviar_recordatorio_pago(venta):
    """Envía recordatorio de pago pendiente"""
    if not venta.cliente or not venta.cliente.email:
        return False
    
    try:
        html_content = render_to_string('core/emails/recordatorio_pago.html', {
            'venta': venta,
            'cliente': venta.cliente,
            'saldo_pendiente': venta.saldo_pendiente,
        })
        
        text_content = strip_tags(html_content)
        
        send_mail(
            subject=f'Recordatorio de Pago - Reserva #{venta.localizador}',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[venta.cliente.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"Recordatorio de pago enviado para venta {venta.id_venta}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando recordatorio pago {venta.id_venta}: {str(e)}")
        return False


def enviar_cambio_estado(venta, estado_anterior):
    """Envía notificación de cambio de estado"""
    if not venta.cliente or not venta.cliente.email:
        return False
    
    try:
        html_content = render_to_string('core/emails/cambio_estado.html', {
            'venta': venta,
            'cliente': venta.cliente,
            'estado_anterior': estado_anterior,
            'estado_actual': venta.get_estado_display(),
        })
        
        text_content = strip_tags(html_content)
        
        send_mail(
            subject=f'Actualización de Reserva #{venta.localizador}',
            message=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[venta.cliente.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"Notificación de cambio de estado enviada para venta {venta.id_venta}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando cambio estado {venta.id_venta}: {str(e)}")
        return False