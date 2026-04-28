"""Módulo unificado de notificaciones"""

from .channels import EmailChannel, WhatsAppChannel
from .service import NotificationService

__all__ = ['EmailChannel', 'WhatsAppChannel', 'NotificationService']
