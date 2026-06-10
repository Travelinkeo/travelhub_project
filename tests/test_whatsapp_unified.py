"""Tests para servicios unificados de comunicación"""

from unittest.mock import Mock, patch

from apps.communications.services.whatsapp_unified import (
    TWILIO_AVAILABLE,
    WhatsAppService,
    enviar_mensaje_meta_api,
    enviar_whatsapp,
    send_whatsapp_message,
)


class TestWhatsAppUnified:
    """Tests para WhatsApp unified service"""

    @patch("apps.communications.services.whatsapp_unified.requests.post")
    def test_enviar_mensaje_meta_api_success(self, mock_post, settings):
        settings.WHATSAPP_TOKEN = "test_token"
        settings.WHATSAPP_PHONE_ID = "test_phone"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "msg1"}]}
        mock_post.return_value = mock_response

        result = enviar_mensaje_meta_api("+1234567890", "Hello", agencia=None)

        assert result["success"] is True
        assert result["provider"] == "meta"

    @patch("apps.communications.services.whatsapp_unified.requests.post")
    def test_enviar_mensaje_meta_api_failure(self, mock_post):
        mock_post.side_effect = Exception("Network error")

        result = enviar_mensaje_meta_api("+1234567890", "Hello")

        assert result["success"] is False

    def test_send_whatsapp_message_no_agencia(self):
        result = send_whatsapp_message("+1234567890", "Hello", agencia=None)
        assert result["success"] is False
        assert "agencia" in result.get("error_message", "").lower() or "subdominio" in result.get(
            "error_message", ""
        )

    @patch("apps.communications.services.whatsapp_unified.EvolutionService.send_text")
    def test_send_whatsapp_message_evolution_success(self, mock_send):
        mock_send.return_value = True
        agencia = Mock()
        agencia.subdominio_slug = "test-agency"

        result = send_whatsapp_message("+1234567890", "Hello", agencia=agencia)

        assert result["success"] is True
        assert result["provider"] == "evolution"

    @patch("apps.communications.services.whatsapp_unified.EvolutionService.send_text")
    @patch("apps.communications.services.whatsapp_unified.enviar_mensaje_meta_api")
    def test_send_whatsapp_message_fallback_to_meta(self, mock_meta, mock_evolution):
        mock_evolution.return_value = False
        mock_meta.return_value = {"success": True, "provider": "meta"}
        agencia = Mock()
        agencia.subdominio_slug = "test-agency"

        result = send_whatsapp_message("+1234567890", "Hello", agencia=agencia)

        assert mock_evolution.called
        assert mock_meta.called


class TestWhatsAppServiceWrapper:
    """Tests para WhatsAppService wrapper"""

    @patch("apps.communications.services.whatsapp_unified.EvolutionService.get_instance_state")
    def test_get_status_open(self, mock_state):
        mock_state.return_value = "open"
        assert WhatsAppService.get_status("test") == "WORKING"

    @patch("apps.communications.services.whatsapp_unified.EvolutionService.get_instance_state")
    def test_get_status_connecting(self, mock_state):
        mock_state.return_value = "connecting"
        assert WhatsAppService.get_status("test") == "CONNECTING"

    @patch("apps.communications.services.whatsapp_unified.EvolutionService.get_instance_state")
    def test_get_status_disconnected(self, mock_state):
        mock_state.return_value = "close"
        assert WhatsAppService.get_status("test") == "DISCONNECTED"

    @patch("apps.communications.services.whatsapp_unified.EvolutionService.create_instance")
    def test_start_session(self, mock_create):
        mock_create.return_value = {"instanceName": "test"}
        result = WhatsAppService.start_session("test")
        assert result is not None

    @patch("apps.communications.services.whatsapp_unified.EvolutionService.delete_instance")
    def test_logout(self, mock_delete):
        mock_delete.return_value = True
        result = WhatsAppService.logout("test")
        assert result is True


class TestTwilioAvailability:
    """Tests para disponibilidad de Twilio"""

    def test_twilio_available_flag(self):
        assert isinstance(TWILIO_AVAILABLE, bool)

    @patch("apps.communications.services.whatsapp_unified.get_twilio_client")
    def test_enviar_whatsapp_no_client(self, mock_client):
        mock_client.return_value = None
        result = enviar_whatsapp("+1234567890", "Hello")
        assert result is False
