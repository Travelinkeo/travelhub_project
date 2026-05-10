import logging
from .evolution_api_service import EvolutionService

logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Wrapper de compatibilidad para migrar de WAHA a Evolution API v2.
    Redirige las llamadas al nuevo EvolutionService manteniendo la interfaz.
    """
    
    @classmethod
    def get_status(cls, session_name: str):
        """Mapea el estado de Evolution a los estados esperados por la UI."""
        state = EvolutionService.get_instance_state(session_name)
        print(f"DEBUG: WhatsAppService.get_status for {session_name} -> RAW STATE: {state}")
        
        if state == 'open':
            print(f"DEBUG: WhatsAppService.get_status -> Returning WORKING")
            return "WORKING"
        elif state == 'connecting':
            print(f"DEBUG: WhatsAppService.get_status -> Returning CONNECTING")
            return "CONNECTING"
        
        print(f"DEBUG: WhatsAppService.get_status -> Returning DISCONNECTED")
        return "DISCONNECTED"

    @classmethod
    def start_session(cls, session_name: str):
        """Crea la instancia en Evolution."""
        return EvolutionService.create_instance(session_name)

    @classmethod
    def get_qr_code(cls, session_name: str):
        """Obtiene el QR de Evolution."""
        qr_data = EvolutionService.get_qr_code(session_name)
        if qr_data and isinstance(qr_data, dict):
            # Evolution v2 retorna un objeto con 'base64'
            return qr_data.get('base64') or qr_data.get('code')
        return qr_data

    @classmethod
    def send_message(cls, chat_id: str, text: str, session_name: str = "default"):
        """Envía mensaje vía Evolution."""
        # Limpiar chat_id si trae sufijos de WAHA
        number = chat_id.replace('@c.us', '').replace('@g.us', '')
        return EvolutionService.send_text(session_name, number, text)

    @classmethod
    def logout(cls, session_name: str):
        """Desconecta y elimina la instancia en Evolution."""
        return EvolutionService.delete_instance(session_name)
