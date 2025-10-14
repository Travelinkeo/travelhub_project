"""
Servicio unificado de notificaciones (Email + WhatsApp)
"""
from django.conf import settings
import logging
from .email_notifications import (
    enviar_confirmacion_venta as email_confirmacion_venta,
    enviar_cambio_estado as email_cambio_estado,
    enviar_recordatorio_pago as email_recordatorio_pago,
    enviar_confirmacion_pago as email_confirmacion_pago
)
from .whatsapp_notifications import (
    enviar_whatsapp_confirmacion_venta,
    enviar_whatsapp_cambio_estado,
    enviar_whatsapp_recordatorio_pago,
    enviar_whatsapp_confirmacion_pago
)

logger = logging.getLogger(__name__)


def notificar_confirmacion_venta(venta):
    """
    Envía notificación de confirmación de venta por todos los canales habilitados
    """
    resultados = {'email': False, 'whatsapp': False}
    
    # Enviar por email
    if venta.cliente and venta.cliente.email:
        resultados['email'] = email_confirmacion_venta(venta)
    
    # Enviar por WhatsApp si está habilitado
    if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        if venta.cliente and venta.cliente.telefono_principal:
            resultados['whatsapp'] = enviar_whatsapp_confirmacion_venta(venta)
    
    logger.info(f"Notificación venta {venta.id_venta}: Email={resultados['email']}, WhatsApp={resultados['whatsapp']}")
    return resultados


def notificar_cambio_estado(venta, estado_anterior):
    """
    Envía notificación de cambio de estado por todos los canales habilitados
    """
    resultados = {'email': False, 'whatsapp': False}
    
    # Enviar por email
    if venta.cliente and venta.cliente.email:
        resultados['email'] = email_cambio_estado(venta, estado_anterior)
    
    # Enviar por WhatsApp si está habilitado
    if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        if venta.cliente and venta.cliente.telefono_principal:
            resultados['whatsapp'] = enviar_whatsapp_cambio_estado(venta, estado_anterior)
    
    logger.info(f"Notificación cambio estado venta {venta.id_venta}: Email={resultados['email']}, WhatsApp={resultados['whatsapp']}")
    return resultados


def notificar_recordatorio_pago(venta):
    """
    Envía recordatorio de pago por todos los canales habilitados
    """
    resultados = {'email': False, 'whatsapp': False}
    
    # Enviar por email
    if venta.cliente and venta.cliente.email:
        resultados['email'] = email_recordatorio_pago(venta)
    
    # Enviar por WhatsApp si está habilitado
    if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        if venta.cliente and venta.cliente.telefono_principal:
            resultados['whatsapp'] = enviar_whatsapp_recordatorio_pago(venta)
    
    logger.info(f"Notificación recordatorio pago venta {venta.id_venta}: Email={resultados['email']}, WhatsApp={resultados['whatsapp']}")
    return resultados


def notificar_confirmacion_pago(pago_venta):
    """
    Envía confirmación de pago por todos los canales habilitados
    """
    resultados = {'email': False, 'whatsapp': False}
    venta = pago_venta.venta
    
    # Enviar por email
    if venta.cliente and venta.cliente.email:
        resultados['email'] = email_confirmacion_pago(pago_venta)
    
    # Enviar por WhatsApp si está habilitado
    if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        if venta.cliente and venta.cliente.telefono_principal:
            resultados['whatsapp'] = enviar_whatsapp_confirmacion_pago(pago_venta)
    
    logger.info(f"Notificación confirmación pago venta {venta.id_venta}: Email={resultados['email']}, WhatsApp={resultados['whatsapp']}")
    return resultados
