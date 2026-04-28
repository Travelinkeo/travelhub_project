"""
Sistema de notificaciones por WhatsApp usando Twilio
"""
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Intentar importar Twilio (opcional)
try:
    from twilio.rest import Client
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio no está instalado. Instala con: pip install twilio")


def get_twilio_client():
    """Obtiene el cliente de Twilio configurado"""
    if not TWILIO_AVAILABLE:
        return None
    
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
    
    if not account_sid or not auth_token:
        logger.warning("Credenciales de Twilio no configuradas")
        return None
    
    return Client(account_sid, auth_token)


def enviar_whatsapp(telefono, mensaje, **kwargs):
    """
    Envía un mensaje de WhatsApp
    
    Args:
        telefono: Número en formato internacional (ej: +584121234567)
        mensaje: Texto del mensaje
        media_url: (Opcional) URL pública del archivo a adjuntar
    """
    client = get_twilio_client()
    if not client:
        logger.warning(f"No se puede enviar WhatsApp a {telefono}: Twilio no disponible")
        return False
    
    try:
        twilio_number = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)
        if not twilio_number:
            logger.error("TWILIO_WHATSAPP_NUMBER no configurado")
            return False
        
        # Asegurar formato whatsapp:+número
        if not telefono.startswith('whatsapp:'):
            telefono = f'whatsapp:{telefono}'
        if not twilio_number.startswith('whatsapp:'):
            twilio_number = f'whatsapp:{twilio_number}'
        
        msg_params = {
            'from_': twilio_number,
            'body': mensaje,
            'to': telefono
        }
        
        # Soporte para adjuntos (PDF/Imagen) si se proporciona URL pública
        if kwargs.get('media_url'):
            msg_params['media_url'] = [kwargs['media_url']]

        message = client.messages.create(**msg_params)
        
        logger.info(f"WhatsApp enviado a {telefono}: {message.sid}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando WhatsApp a {telefono}: {e}")
        return False


def enviar_whatsapp_confirmacion_venta(venta):
    """Envía WhatsApp de confirmación cuando se crea una venta"""
    if not venta.cliente or not venta.cliente.telefono_principal:
        logger.warning(f"Venta {venta.id_venta} sin cliente o teléfono")
        return False
    
    mensaje = f"""
🌍 *TravelHub - Confirmación de Reserva*

Estimado/a *{venta.cliente.get_nombre_completo()}*,

Su reserva ha sido creada exitosamente.

📋 *Detalles:*
• Localizador: *{venta.localizador}*
• Fecha: {venta.fecha_venta.strftime('%d/%m/%Y')}
• Total: {venta.moneda.simbolo if venta.moneda else ''}{venta.total_venta}
• Estado: {venta.get_estado_display()}

Gracias por confiar en nosotros.

_Equipo TravelHub_
""".strip()
    
    return enviar_whatsapp(venta.cliente.telefono_principal, mensaje)


def enviar_whatsapp_cambio_estado(venta, estado_anterior):
    """Envía WhatsApp cuando cambia el estado de la venta"""
    if not venta.cliente or not venta.cliente.telefono_principal:
        return False
    
    mensaje = f"""
🔄 *TravelHub - Actualización de Reserva*

Estimado/a *{venta.cliente.get_nombre_completo()}*,

El estado de su reserva ha sido actualizado.

📋 *Detalles:*
• Localizador: *{venta.localizador}*
• Estado anterior: {estado_anterior}
• Estado actual: *{venta.get_estado_display()}*

Si tiene alguna pregunta, no dude en contactarnos.

_Equipo TravelHub_
""".strip()
    
    return enviar_whatsapp(venta.cliente.telefono_principal, mensaje)


def enviar_whatsapp_recordatorio_pago(venta):
    """Envía recordatorio de pago pendiente por WhatsApp"""
    if not venta.cliente or not venta.cliente.telefono_principal:
        return False
    
    if venta.saldo_pendiente <= 0:
        return False
    
    mensaje = f"""
⏰ *TravelHub - Recordatorio de Pago*

Estimado/a *{venta.cliente.get_nombre_completo()}*,

Le recordamos que tiene un saldo pendiente en su reserva.

📋 *Detalles:*
• Localizador: *{venta.localizador}*
• Total: {venta.moneda.simbolo if venta.moneda else ''}{venta.total_venta}
• Pagado: {venta.moneda.simbolo if venta.moneda else ''}{venta.total_venta - venta.saldo_pendiente}
• *Saldo pendiente: {venta.moneda.simbolo if venta.moneda else ''}{venta.saldo_pendiente}*

Por favor, proceda con el pago para confirmar su reserva.

_Equipo TravelHub_
""".strip()
    
    return enviar_whatsapp(venta.cliente.telefono_principal, mensaje)


def enviar_whatsapp_confirmacion_pago(pago_venta):
    """Envía confirmación cuando se registra un pago por WhatsApp"""
    venta = pago_venta.venta
    if not venta.cliente or not venta.cliente.telefono_principal:
        return False
    
    saldo_msg = "✅ *Su reserva está completamente pagada.*" if venta.saldo_pendiente <= 0 else f"Saldo restante: {venta.moneda.simbolo if venta.moneda else ''}{venta.saldo_pendiente}"
    
    mensaje = f"""
💰 *TravelHub - Confirmación de Pago*

Estimado/a *{venta.cliente.get_nombre_completo()}*,

Hemos recibido su pago correctamente. ¡Gracias!

📋 *Detalles del pago:*
• Localizador: *{venta.localizador}*
• Monto pagado: {pago_venta.moneda.simbolo if pago_venta.moneda else ''}{pago_venta.monto}
• Fecha: {pago_venta.fecha_pago.strftime('%d/%m/%Y')}
• Método: {pago_venta.get_metodo_display()}

{saldo_msg}

_Equipo TravelHub_
""".strip()
    
    return enviar_whatsapp(venta.cliente.telefono_principal, mensaje)
