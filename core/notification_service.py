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
    try:
        if venta.cliente and venta.cliente.email:
            resultados['email'] = email_confirmacion_venta(venta)
    except Exception as e:
        logger.warning(f"Error accediendo a cliente en confirmación venta: {e}")

    # Enviar por WhatsApp si está habilitado
    if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        try:
            if venta.cliente and venta.cliente.telefono_principal:
                resultados['whatsapp'] = enviar_whatsapp_confirmacion_venta(venta)
        except Exception as e:
            logger.warning(f"Error accediendo a cliente en whatsapp venta: {e}")
    
    logger.info(f"Notificación venta {venta.id_venta}: Email={resultados['email']}, WhatsApp={resultados['whatsapp']}")
    return resultados


def notificar_cambio_estado(venta, estado_anterior):
    """
    Envía notificación de cambio de estado por todos los canales habilitados
    """
    resultados = {'email': False, 'whatsapp': False}
    
    # Enviar por email
    try:
        if venta.cliente and venta.cliente.email:
            resultados['email'] = email_cambio_estado(venta, estado_anterior)
    except Exception as e:
         logger.warning(f"Error accediendo a cliente en cambio estado: {e}")
    
    # Enviar por WhatsApp si está habilitado
    if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        try:
            if venta.cliente and venta.cliente.telefono_principal:
                resultados['whatsapp'] = enviar_whatsapp_cambio_estado(venta, estado_anterior)
        except Exception as e:
            logger.warning(f"Error accediendo a cliente en whatsapp cambio estado: {e}")
    
    logger.info(f"Notificación cambio estado venta {venta.id_venta}: Email={resultados['email']}, WhatsApp={resultados['whatsapp']}")
    return resultados


def notificar_recordatorio_pago(venta):
    """
    Envía recordatorio de pago por todos los canales habilitados
    """
    resultados = {'email': False, 'whatsapp': False}
    
    # Enviar por email
    try:
        if venta.cliente and venta.cliente.email:
            resultados['email'] = email_recordatorio_pago(venta)
    except Exception as e:
        logger.warning(f"Error accediendo a cliente en recordatorio pago: {e}")
    
    # Enviar por WhatsApp si está habilitado
    if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        try:
            if venta.cliente and venta.cliente.telefono_principal:
                resultados['whatsapp'] = enviar_whatsapp_recordatorio_pago(venta)
        except Exception as e:
             logger.warning(f"Error accediendo a cliente en whatsapp recordatorio: {e}")
    
    logger.info(f"Notificación recordatorio pago venta {venta.id_venta}: Email={resultados['email']}, WhatsApp={resultados['whatsapp']}")
    return resultados


def notificar_confirmacion_pago(pago_venta):
    """
    Envía confirmación de pago por todos los canales habilitados
    """
    resultados = {'email': False, 'whatsapp': False}
    venta = pago_venta.venta
    
    # Enviar por email
    try:
        if venta.cliente and venta.cliente.email:
            resultados['email'] = email_confirmacion_pago(pago_venta)
    except Exception as e:
         logger.warning(f"Error accediendo a cliente en confirmacion pago: {e}")
    
    # Enviar por WhatsApp si está habilitado
    if getattr(settings, 'WHATSAPP_NOTIFICATIONS_ENABLED', False):
        try:
            if venta.cliente and venta.cliente.telefono_principal:
                resultados['whatsapp'] = enviar_whatsapp_confirmacion_pago(pago_venta)
        except Exception as e:
            logger.warning(f"Error accediendo a cliente en whatsapp confirmacion pago: {e}")
    
    logger.info(f"Notificación confirmación pago venta {venta.id_venta}: Email={resultados['email']}, WhatsApp={resultados['whatsapp']}")
    return resultados


def notificar_alerta_migratoria(migration_check):
    """
    Envía una alerta proactiva por Telegram si el chequeo migratorio es ROJO o AMARILLO.
    """
    if migration_check.alert_level == 'GREEN':
        return False

    from asgiref.sync import async_to_sync
    from telegram import Bot
    from django.conf import settings
    from core.models import UsuarioAgencia

    # 1. Obtener al usuario destinatario
    # Intentamos notificar al usuario que creó la venta o al dueño de la agencia
    venta = migration_check.venta
    if not venta:
        return False
        
    usuarios_candidatos = []
    
    # Opción A: Creador de la venta
    if venta.creado_por:
        usuarios_candidatos = UsuarioAgencia.objects.filter(usuario=venta.creado_por)
    
    # Opción B: Si no hay creador (importación auto), notificar al admin de la agencia
    if not usuarios_candidatos and venta.agencia:
        usuarios_candidatos = UsuarioAgencia.objects.filter(
            agencia=venta.agencia, 
            rol__in=['admin', 'gerente']
        )
    
    # Filtrar los que tengan Telegram ID
    destinatarios = [u for u in usuarios_candidatos if u.telegram_chat_id]
    
    if not destinatarios:
        logger.warning(f"No se encontraron destinatarios con Telegram ID para alerta migratoria de Venta {venta.localizador}")
        return False

    # 2. Construir mensaje
    emoji = migration_check.get_alert_emoji()
    msg = (
        f"{emoji} **ALERTA MIGRATORIA**\n\n"
        f"👮‍♂️ **Pasajero:** {str(migration_check.pasajero)}\n"
        f"✈️ **Ruta:** {migration_check.origen} ➡️ {migration_check.destino}\n"
        f"⚠️ **Nivel:** {migration_check.get_alert_level_display()}\n\n"
        f"📝 **Resumen:** {migration_check.summary}\n\n"
        f"🔗 Revise la Venta `{venta.localizador}` en el sistema."
    )

    # 3. Enviar (Async wrap)
    # 3. Enviar (Async wrap -> Sync via Service)
    from core.services.telegram_notification_service import TelegramNotificationService
    
    # El servicio ya maneja el token y chat ID de la agencia/usuario si se le pasa
    # Pero aquí tenemos destinatarios individuales (usuarios).
    # TelegramNotificationService.send_message usa config de agencia o chat_id explicito.
    
    for usuario in destinatarios:
        try:
            # Usamos el servicio pasando el chat_id explícito del usuario
            # Y la agencia para que el servicio use el Token correcto de esa agencia
            TelegramNotificationService.send_message(
                message=msg,
                chat_id=usuario.telegram_chat_id,
                parse_mode='Markdown',
                agencia=venta.agencia
            )
            logger.info(f"Alerta migratoria enviada a {usuario.usuario.username} ({usuario.telegram_chat_id})")
        except Exception as e:
            logger.error(f"Error enviando Telegram a {usuario.usuario.username}: {e}")

    try:
        async_to_sync(send_all)()
        return True
    except Exception as e:
        logger.error(f"Error general enviando alertas migratorias: {e}")
        return False
