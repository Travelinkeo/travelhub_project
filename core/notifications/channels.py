"""Canales de notificación unificados"""
from abc import ABC, abstractmethod
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Interfaz base para canales de notificación"""
    
    @abstractmethod
    def send(self, recipient: str, message: str, **kwargs) -> bool:
        """Envía notificación por este canal"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica si el canal está disponible"""
        pass


class EmailChannel(NotificationChannel):
    """Canal de notificación por email"""
    
    def send(self, recipient: str, message: str, **kwargs) -> bool:
        try:
            from core.email_notifications import enviar_email_generico
            subject = kwargs.get('subject', 'Notificación TravelHub')
            return enviar_email_generico(recipient, subject, message)
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return False
    
    def is_available(self) -> bool:
        return bool(settings.EMAIL_HOST_USER)


class WhatsAppChannel(NotificationChannel):
    """Canal de notificación por WhatsApp"""
    
    def send(self, recipient: str, message: str, **kwargs) -> bool:
        try:
            from core.whatsapp_notifications import enviar_whatsapp
            return enviar_whatsapp(recipient, message)
        except Exception as e:
            logger.error(f"Error enviando WhatsApp: {e}")
            return False
    
    def is_available(self) -> bool:
        return settings.WHATSAPP_NOTIFICATIONS_ENABLED
