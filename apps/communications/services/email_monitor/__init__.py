"""
Email Monitor Service - Refactored Module

Este módulo refactorizado divide la God Class original (email_unified.py) en
componentes más pequeños y mantenibles.

Estructura:
- email_sender.py: Funciones de envío de emails
- email_monitor_service.py: Servicio principal de monitoreo
- email_parser.py: Parseo y extracción de contenido de emails
- notification_dispatcher.py: Envío de notificaciones (Telegram, WhatsApp, etc.)
- pdf_validator.py: Validación y procesamiento de PDFs
- drive_uploader.py: Upload de archivos a Google Drive
"""

from .email_monitor_service import EmailMonitorService
from .email_sender import (
    enviar_cambio_estado,
    enviar_confirmacion_pago,
    enviar_confirmacion_venta,
    enviar_email_generico,
    enviar_email_html,
    enviar_recordatorio_pago,
    send_custom_email,
)

__all__ = [
    "send_custom_email",
    "enviar_email_generico",
    "enviar_email_html",
    "enviar_confirmacion_venta",
    "enviar_recordatorio_pago",
    "enviar_cambio_estado",
    "enviar_confirmacion_pago",
    "EmailMonitorService",
]
