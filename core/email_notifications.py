"""
Sistema de notificaciones por email para eventos de ventas
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage
import logging
import os

logger = logging.getLogger(__name__)


def enviar_email_html(asunto, template_name, context, destinatario):
    """Función auxiliar para enviar emails HTML con logo embebido"""
    try:
        html_content = render_to_string(template_name, context)
        
        email = EmailMultiAlternatives(
            asunto,
            f"Este email requiere un cliente que soporte HTML. Contenido: {context.get('localizador', '')}",
            settings.DEFAULT_FROM_EMAIL,
            [destinatario]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Adjuntar logo como imagen embebida
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo-blanco.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
                logo_image = MIMEImage(logo_data)
                logo_image.add_header('Content-ID', '<logo>')
                logo_image.add_header('Content-Disposition', 'inline', filename='logo-blanco.png')
                email.attach(logo_image)
        
        email.send(fail_silently=False)
        return True
    except Exception as e:
        logger.error(f"Error enviando email HTML: {e}")
        return False


def enviar_confirmacion_venta(venta):
    """Envía email de confirmación cuando se crea una venta"""
    if not venta.cliente or not venta.cliente.email:
        logger.warning(f"Venta {venta.id_venta} sin cliente o email")
        return False
    
    context = {
        'cliente_nombre': venta.cliente.get_nombre_completo(),
        'localizador': venta.localizador,
        'fecha': venta.fecha_venta.strftime('%d/%m/%Y'),
        'total': venta.total_venta,
        'moneda': venta.moneda.simbolo if venta.moneda else '',
        'estado': venta.get_estado_display()
    }
    
    resultado = enviar_email_html(
        f'Confirmación de Reserva - {venta.localizador}',
        'core/emails/confirmacion_venta.html',
        context,
        venta.cliente.email
    )
    
    if resultado:
        logger.info(f"Email confirmación enviado para venta {venta.id_venta}")
    return resultado


def enviar_cambio_estado(venta, estado_anterior):
    """Envía email cuando cambia el estado de la venta"""
    if not venta.cliente or not venta.cliente.email:
        return False
    
    context = {
        'cliente_nombre': venta.cliente.get_nombre_completo(),
        'localizador': venta.localizador,
        'estado_anterior': estado_anterior,
        'estado_actual': venta.get_estado_display()
    }
    
    resultado = enviar_email_html(
        f'Actualización de Reserva - {venta.localizador}',
        'core/emails/cambio_estado.html',
        context,
        venta.cliente.email
    )
    
    if resultado:
        logger.info(f"Email cambio estado enviado para venta {venta.id_venta}")
    return resultado


def enviar_recordatorio_pago(venta):
    """Envía recordatorio de pago pendiente"""
    if not venta.cliente or not venta.cliente.email:
        return False
    
    if venta.saldo_pendiente <= 0:
        return False
    
    context = {
        'cliente_nombre': venta.cliente.get_nombre_completo(),
        'localizador': venta.localizador,
        'total': venta.total_venta,
        'pagado': venta.total_venta - venta.saldo_pendiente,
        'saldo': venta.saldo_pendiente,
        'moneda': venta.moneda.simbolo if venta.moneda else ''
    }
    
    resultado = enviar_email_html(
        f'Recordatorio de Pago - {venta.localizador}',
        'core/emails/recordatorio_pago.html',
        context,
        venta.cliente.email
    )
    
    if resultado:
        logger.info(f"Email recordatorio pago enviado para venta {venta.id_venta}")
    return resultado


def enviar_confirmacion_pago(pago_venta):
    """Envía confirmación cuando se registra un pago"""
    venta = pago_venta.venta
    if not venta.cliente or not venta.cliente.email:
        return False
    
    context = {
        'cliente_nombre': venta.cliente.get_nombre_completo(),
        'localizador': venta.localizador,
        'monto': pago_venta.monto,
        'fecha': pago_venta.fecha_pago.strftime('%d/%m/%Y'),
        'metodo': pago_venta.get_metodo_display(),
        'saldo': venta.saldo_pendiente,
        'moneda': pago_venta.moneda.simbolo if pago_venta.moneda else ''
    }
    
    resultado = enviar_email_html(
        f'Confirmación de Pago - {venta.localizador}',
        'core/emails/confirmacion_pago.html',
        context,
        venta.cliente.email
    )
    
    if resultado:
        logger.info(f"Email confirmación pago enviado para venta {venta.id_venta}")
    return resultado
