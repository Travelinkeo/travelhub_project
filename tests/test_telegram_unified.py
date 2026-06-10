"""Tests para servicios unificados de Telegram"""

from unittest.mock import Mock, patch

from apps.communications.services.telegram_unified import (
    TelegramNotificationService,
    enviar_alerta_telegram,
    get_telegram_file_url,
    upload_logo_to_telegram,
)


class TestTelegramNotificationService:
    """Tests para TelegramNotificationService"""

    @patch("apps.communications.services.telegram_unified.requests.post")
    def test_send_message_success(self, mock_post, settings):
        settings.TELEGRAM_BOT_TOKEN = "test_token"
        settings.TELEGRAM_GROUP_ID = "-1001234567890"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = TelegramNotificationService.send_message("Test message")

        assert result is True
        mock_post.assert_called_once()

    @patch("apps.communications.services.telegram_unified.requests.post")
    def test_send_message_no_config(self, mock_post, settings):
        settings.TELEGRAM_BOT_TOKEN = None
        settings.TELEGRAM_GROUP_ID = None

        result = TelegramNotificationService.send_message("Test message")

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.communications.services.telegram_unified.requests.post")
    def test_send_message_exception(self, mock_post, settings):
        settings.TELEGRAM_BOT_TOKEN = "test_token"
        settings.TELEGRAM_GROUP_ID = "-1001234567890"
        mock_post.side_effect = Exception("Network error")

        result = TelegramNotificationService.send_message("Test message")

        assert result is False


class TestEnviarAlertaTelegram:
    """Tests para enviar_alerta_telegram"""

    @patch("apps.communications.services.telegram_unified.TelegramNotificationService.send_message")
    def test_enviar_alerta_success(self, mock_send):
        mock_send.return_value = True

        result = enviar_alerta_telegram("Test alert")

        assert result is True
        mock_send.assert_called_once_with("Test alert", chat_id=None, agencia=None)

    @patch("apps.communications.services.telegram_unified.TelegramNotificationService.send_message")
    def test_enviar_alerta_failure(self, mock_send):
        mock_send.return_value = False

        result = enviar_alerta_telegram("Test alert")

        assert result is False


class TestTelegramStorage:
    """Tests para funciones de almacenamiento"""

    @patch("apps.communications.services.telegram_unified.requests.post")
    def test_upload_logo_success(self, mock_post, settings):
        settings.TELEGRAM_BOT_TOKEN = "test_token"
        settings.TELEGRAM_STORAGE_CHANNEL_ID = "-1001234567890"

        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "result": {"photo": [{"file_id": "file1"}, {"file_id": "file2"}]},
        }
        mock_post.return_value = mock_response

        file_obj = Mock()
        file_obj.read.return_value = b"fake image data"
        file_obj.seek = Mock()

        result = upload_logo_to_telegram(file_obj, "logo.png")

        assert result == "file2"
        mock_post.assert_called_once()

    @patch("apps.communications.services.telegram_unified.requests.post")
    def test_upload_logo_no_config(self, mock_post, settings):
        settings.TELEGRAM_BOT_TOKEN = None
        settings.TELEGRAM_STORAGE_CHANNEL_ID = None

        file_obj = Mock()
        result = upload_logo_to_telegram(file_obj)

        assert result is None
        mock_post.assert_not_called()

    def test_get_telegram_file_url_success(self, settings):
        settings.TELEGRAM_BOT_TOKEN = "test_token"

        result = get_telegram_file_url("file_id_123")

        assert "test_token" in result
        assert "file_id_123" in result

    def test_get_telegram_file_url_no_token(self, settings):
        settings.TELEGRAM_BOT_TOKEN = None

        result = get_telegram_file_url("file_id_123")

        assert result is None

    def test_get_telegram_file_url_no_file_id(self, settings):
        settings.TELEGRAM_BOT_TOKEN = "test_token"

        result = get_telegram_file_url(None)

        assert result is None
