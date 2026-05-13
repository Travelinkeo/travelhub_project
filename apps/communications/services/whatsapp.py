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
        logger.info(f"WhatsAppService.get_status for {session_name} -> {state}")

        if state == "open":
            return "WORKING"
        elif state == "connecting":
            return "CONNECTING"

        return "DISCONNECTED"

    @classmethod
    def start_session(cls, session_name: str):
        """Crea la instancia en Evolution."""
        return EvolutionService.create_instance(session_name)

    @classmethod
    def get_qr_code(cls, session_name: str):
        """
        Obtiene el QR de Evolution.

        Evolution API v2.2.x no expone QR via REST. Retorna la URL del Manager UI
        donde el usuario puede ver/escanear el QR para vincular WhatsApp.
        """
        qr_data = EvolutionService.get_qr_code(session_name)

        if qr_data:
            if isinstance(qr_data, str):
                base64 = qr_data
            elif isinstance(qr_data, dict):
                base64 = qr_data.get("base64") or qr_data.get("code")
                if not base64:
                    base64 = None
            else:
                base64 = None

            if base64 and isinstance(base64, str):
                if base64.startswith("data:image"):
                    return base64
                return f"data:image/png;base64,{base64}"

        return EvolutionService.get_manager_qr_url(session_name)

    @classmethod
    def send_message(cls, chat_id: str, text: str, session_name: str = "default"):
        """Envía mensaje vía Evolution."""
        number = chat_id.replace("@c.us", "").replace("@g.us", "")
        return EvolutionService.send_text(session_name, number, text)

    @classmethod
    def logout(cls, session_name: str):
        """Desconecta y elimina la instancia en Evolution."""
        return EvolutionService.delete_instance(session_name)
