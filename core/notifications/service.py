"""Servicio unificado de notificaciones"""
import logging
from typing import Dict, Any

from .channels import EmailChannel, WhatsAppChannel

logger = logging.getLogger(__name__)


class NotificationService:
    """Servicio centralizado para envío de notificaciones"""
    
    def __init__(self):
        self.channels = {
            'email': EmailChannel(),
            'whatsapp': WhatsAppChannel(),
        }
    
    def notify(self, event: str, recipient: dict, data: dict) -> Dict[str, bool]:
        """
        Envía notificación por todos los canales disponibles
        
        Args:
            event: Tipo de evento (confirmacion_venta, cambio_estado, etc.)
            recipient: Dict con email y telefono del destinatario
            data: Datos para construir el mensaje
            
        Returns:
            Dict con resultado por canal
        """
        results = {}
        
        for channel_name, channel in self.channels.items():
            if not channel.is_available():
                logger.debug(f"Canal {channel_name} no disponible")
                continue
            
            recipient_id = self._get_recipient_for_channel(recipient, channel_name)
            if not recipient_id:
                logger.debug(f"No hay destinatario para canal {channel_name}")
                continue
            
            message = self._build_message(event, data, channel_name)
            results[channel_name] = channel.send(recipient_id, message, **data)
        
        return results
    
    def _get_recipient_for_channel(self, recipient: dict, channel: str) -> str:
        """Obtiene el destinatario apropiado para el canal"""
        if channel == 'email':
            return recipient.get('email')
        elif channel == 'whatsapp':
            return recipient.get('telefono')
        return None
    
    def _build_message(self, event: str, data: dict, channel: str) -> str:
        """Construye el mensaje según el evento y canal"""
        # Usar templates existentes
        if event == 'confirmacion_venta':
            return self._build_venta_message(data, channel)
        elif event == 'cambio_estado':
            return self._build_estado_message(data, channel)
        elif event == 'recordatorio_pago':
            return self._build_pago_message(data, channel)
        return str(data)
    
    def _build_venta_message(self, data: dict, channel: str) -> str:
        venta = data.get('venta')
        if channel == 'whatsapp':
            return f"✅ Venta confirmada\nLocalizador: {venta.localizador}\nTotal: {venta.total_venta}"
        return f"Su venta {venta.localizador} ha sido confirmada."
    
    def _build_estado_message(self, data: dict, channel: str) -> str:
        venta = data.get('venta')
        estado = data.get('estado_nuevo')
        return f"Estado de venta {venta.localizador} cambió a: {estado}"
    
    def _build_pago_message(self, data: dict, channel: str) -> str:
        venta = data.get('venta')
        return f"Recordatorio: Pago pendiente para venta {venta.localizador}"


# Instancia global del servicio
notification_service = NotificationService()
