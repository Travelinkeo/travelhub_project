"""Tests para sistema de notificaciones unificado"""

from unittest.mock import Mock, patch

from apps.communications.services.notification_dispatcher import (
    EmailChannel,
    NotificationDispatcher,
    TelegramChannel,
    WhatsAppChannel,
    enviar_recordatorio_vuelo,
    notificar_alerta_migratoria,
    notificar_boleto_procesado,
)


class TestEmailChannel:
    """Tests para EmailChannel"""

    def test_is_available_with_email_configured(self, settings):
        """Is available with email configured."""
        settings.EMAIL_HOST_USER = "test@example.com"
        channel = EmailChannel()
        assert channel.is_available() is True

    def test_is_available_without_email(self, settings):
        """Is available without email."""
        settings.EMAIL_HOST_USER = ""
        channel = EmailChannel()
        assert channel.is_available() is False

    @patch("apps.common.tasks.send_email_task.delay")
    def test_send_email_success(self, mock_email):
        """Send email success."""
        mock_email.return_value = True
        channel = EmailChannel()
        result = channel.send("test@example.com", "Test message", subject="Test")
        assert result is True
        mock_email.assert_called_once()

    @patch("apps.common.tasks.send_email_task.delay")
    def test_send_email_failure(self, mock_email):
        """Send email failure."""
        mock_email.side_effect = Exception("Email error")
        channel = EmailChannel()
        result = channel.send("test@example.com", "Test message")
        assert result is False


class TestWhatsAppChannel:
    """Tests para WhatsAppChannel"""

    def test_is_available_enabled(self, settings):
        """Is available enabled."""
        settings.WHATSAPP_NOTIFICATIONS_ENABLED = True
        channel = WhatsAppChannel()
        assert channel.is_available() is True

    def test_is_available_disabled(self, settings):
        """Is available disabled."""
        settings.WHATSAPP_NOTIFICATIONS_ENABLED = False
        channel = WhatsAppChannel()
        assert channel.is_available() is False

    @patch("apps.common.tasks.send_whatsapp_task.delay")
    def test_send_whatsapp_success(self, mock_whatsapp):
        """Send whatsapp success."""
        mock_whatsapp.return_value = True
        channel = WhatsAppChannel()
        result = channel.send("+1234567890", "Test message")
        assert result is True

    @patch("apps.common.tasks.send_whatsapp_task.delay")
    def test_send_whatsapp_failure(self, mock_whatsapp):
        """Send whatsapp failure."""
        mock_whatsapp.side_effect = Exception("WhatsApp error")
        channel = WhatsAppChannel()
        result = channel.send("+1234567890", "Test message")
        assert result is False


class TestNotificationDispatcher:
    """Tests para NotificationDispatcher"""

    @patch("apps.communications.services.notification_dispatcher.EmailChannel")
    @patch("apps.communications.services.notification_dispatcher.WhatsAppChannel")
    @patch("apps.communications.services.notification_dispatcher.TelegramChannel")
    def test_notify_all_channels(self, mock_telegram_class, mock_whatsapp_class, mock_email_class):
        """Notify all channels."""
        mock_email = Mock()
        mock_email.is_available.return_value = True
        mock_email.send.return_value = True
        mock_email_class.return_value = mock_email

        mock_whatsapp = Mock()
        mock_whatsapp.is_available.return_value = True
        mock_whatsapp.send.return_value = True
        mock_whatsapp_class.return_value = mock_whatsapp

        mock_telegram = Mock()
        mock_telegram.is_available.return_value = True
        mock_telegram.send.return_value = True
        mock_telegram_class.return_value = mock_telegram

        service = NotificationDispatcher()
        recipient = {
            "email": "test@example.com",
            "telefono": "+1234567890",
            "telegram_chat_id": "123456",
        }
        results = service.notify("confirmacion_venta", recipient, {"venta": Mock()})

        assert results["email"] is True
        assert results["whatsapp"] is True
        assert results["telegram"] is True

    def test_get_recipient_for_channel_email(self):
        """Get recipient for channel email."""
        service = NotificationDispatcher()
        recipient = {"email": "test@example.com", "telefono": "+1234567890"}
        result = service._get_recipient_for_channel(recipient, "email")
        assert result == "test@example.com"

    def test_get_recipient_for_channel_whatsapp(self):
        """Get recipient for channel whatsapp."""
        service = NotificationDispatcher()
        recipient = {"email": "test@example.com", "telefono": "+1234567890"}
        result = service._get_recipient_for_channel(recipient, "whatsapp")
        assert result == "+1234567890"

    def test_get_recipient_for_channel_unknown(self):
        """Get recipient for channel unknown."""
        service = NotificationDispatcher()
        recipient = {"email": "test@example.com", "telefono": "+1234567890"}
        result = service._get_recipient_for_channel(recipient, "unknown")
        assert result is None


class TestPaymentNotifications:
    """Tests para notificaciones de pago"""

    @patch("apps.communications.services.email_unified.enviar_confirmacion_pago")
    @patch("apps.communications.services.whatsapp_unified.enviar_whatsapp_confirmacion_pago")
    def test_notificar_confirmacion_pago(self, mock_wa, mock_email):
        """Test that payment confirmation orchestrator calls both channels"""
        from apps.communications.services.notification_dispatcher import (
            notificar_confirmacion_pago as notif,
        )

        pago_venta = Mock()
        notif(pago_venta)
        assert mock_email.called or mock_wa.called

    @patch("apps.communications.services.email_unified.enviar_recordatorio_pago")
    @patch("apps.communications.services.whatsapp_unified.enviar_whatsapp_recordatorio_pago")
    def test_notificar_recordatorio_pago(self, mock_wa, mock_email):
        """Test that payment reminder orchestrator calls both channels"""
        from apps.communications.services.notification_dispatcher import (
            notificar_recordatorio_pago as notif,
        )

        venta = Mock()
        result = notif(venta)
        assert isinstance(result, dict)
        assert "email" in result
        assert "whatsapp" in result


class TestAlertNotifications:
    """Tests para alertas migratorias"""

    @patch("apps.common.tasks.send_whatsapp_task.delay")
    @patch("apps.common.tasks.send_telegram_task.delay")
    def test_notificar_alerta_migratoria(self, mock_telegram, mock_whatsapp, settings):
        """Notificar alerta migratoria."""
        settings.ADMIN_WHATSAPP_NUMBER = "+1234567890"
        check_instance = Mock()
        check_instance.localizador = "ABC123"
        check_instance.pasajero_nombre = "John Doe"
        check_instance.alert_level = "HIGH"
        check_instance.summary = "Visa required"

        notificar_alerta_migratoria(check_instance)

        mock_whatsapp.assert_called_once()
        mock_telegram.assert_called_once()


class TestTicketNotifications:
    """Tests para notificaciones de boletos"""

    @patch("apps.common.tasks.send_whatsapp_task.delay")
    @patch("django.core.mail.send_mail")
    def test_notificar_boleto_procesado_admin_only(self, mock_email, mock_whatsapp, settings):
        """Notificar boleto procesado admin only."""
        settings.ADMIN_WHATSAPP_NUMBER = "+1234567890"
        settings.WHATSAPP_NOTIFICATIONS_ENABLED = True

        boleto = Mock()
        boleto.venta_asociada = None
        boleto.datos_parseados = {
            "normalized": {"reservation_code": "ABC123", "passenger_name": "John Doe"}
        }
        boleto.localizador_pnr = "ABC123"
        boleto.nombre_pasajero_procesado = "John Doe"
        boleto.aerolinea_emisora = "AA"
        boleto.numero_boleto = "1234567890"
        boleto.archivo_pdf_generado = None

        result = notificar_boleto_procesado(boleto)

        assert result is True
        mock_whatsapp.assert_called_once()

    @patch("apps.common.tasks.send_whatsapp_task.delay")
    def test_enviar_recordatorio_vuelo(self, mock_whatsapp):
        """Enviar recordatorio vuelo."""
        cliente = Mock()
        cliente.telefono_principal = "+1234567890"
        cliente.get_nombre_completo.return_value = "John Doe"

        venta = Mock()
        venta.cliente = cliente

        boleto = Mock()
        boleto.venta_asociada = venta
        boleto.datos_parseados = {
            "normalized": {
                "reservation_code": "ABC123",
                "passenger_name": "John Doe",
                "flights": [
                    {"origin": "CCS", "destination": "MIA", "date": "2024-01-01", "time": "10:00"}
                ],
            }
        }
        boleto.localizador_pnr = "ABC123"
        boleto.nombre_pasajero_procesado = "John Doe"
        boleto.aerolinea_emisora = "AA"

        result = enviar_recordatorio_vuelo(boleto, horas_antes=24)

        assert result is True
        mock_whatsapp.assert_called_once()

    def test_enviar_recordatorio_vuelo_no_venta(self):
        """Enviar recordatorio vuelo no venta."""
        boleto = Mock()
        boleto.venta_asociada = None
        result = enviar_recordatorio_vuelo(boleto)
        assert result is False

    def test_enviar_recordatorio_vuelo_no_flights(self):
        """Enviar recordatorio vuelo no flights."""
        cliente = Mock()
        cliente.telefono_principal = "+1234567890"
        venta = Mock()
        venta.cliente = cliente
        boleto = Mock()
        boleto.venta_asociada = venta
        boleto.datos_parseados = {
            "normalized": {"reservation_code": "ABC123", "passenger_name": "John", "flights": []}
        }
        boleto.localizador_pnr = "ABC123"
        boleto.nombre_pasajero_procesado = "John"
        boleto.aerolinea_emisora = "AA"
        result = enviar_recordatorio_vuelo(boleto)
        assert result is False


class TestTelegramChannel:
    """Tests para TelegramChannel"""

    def test_is_available_enabled(self, settings):
        """Is available enabled."""
        settings.TELEGRAM_BOT_TOKEN = "token"
        settings.TELEGRAM_GROUP_ID = "group"
        channel = TelegramChannel()
        assert channel.is_available() is True

    def test_is_available_disabled(self, settings):
        """Is available disabled."""
        settings.TELEGRAM_BOT_TOKEN = ""
        channel = TelegramChannel()
        assert channel.is_available() is False

    @patch("apps.common.tasks.send_telegram_task.delay")
    def test_send_telegram_success(self, mock_telegram):
        """Send telegram success."""
        mock_telegram.return_value = True
        channel = TelegramChannel()
        result = channel.send("group123", "Test message")
        assert result is True

    @patch("apps.common.tasks.send_telegram_task.delay")
    def test_send_telegram_failure(self, mock_telegram):
        """Send telegram failure."""
        mock_telegram.side_effect = Exception("Telegram error")
        channel = TelegramChannel()
        result = channel.send("group123", "Test message")
        assert result is False


class TestMultiTenantNotifications:
    """Tests para comportamiento multi-tenant de los canales de notificación"""

    def test_email_channel_available_with_agency_smtp(self):
        """Email channel available with agency smtp."""
        agencia = Mock()
        agencia.configuracion_correo = {
            "EMAIL_HOST": "smtp.tenant.com",
            "EMAIL_PORT": 587,
            "EMAIL_HOST_USER": "user@tenant.com",
        }
        channel = EmailChannel()
        assert channel.is_available(agencia=agencia) is True

    @patch("apps.common.tasks.send_email_task.delay")
    def test_email_channel_send_uses_agency_context(self, mock_send_email):
        """Email channel send uses agency context."""
        agencia = Mock()
        agencia.configuracion_correo = {
            "EMAIL_HOST": "smtp.tenant.com",
            "EMAIL_PORT": 587,
            "EMAIL_HOST_USER": "user@tenant.com",
        }
        channel = EmailChannel()
        channel.send("test@recipient.com", "Hello", agencia=agencia)
        mock_send_email.assert_called_once()

    def test_whatsapp_channel_available_with_agency_subdomain(self):
        """Whatsapp channel available with agency subdomain."""
        agencia = Mock()
        agencia.subdominio_slug = "mytenant"
        channel = WhatsAppChannel()
        assert channel.is_available(agencia=agencia) is True

    @patch("apps.common.tasks.send_whatsapp_task.delay")
    def test_whatsapp_channel_send_uses_agency_context(self, mock_send_wa):
        """Whatsapp channel send uses agency context."""
        agencia = Mock()
        agencia.subdominio_slug = "mytenant"
        channel = WhatsAppChannel()
        channel.send("+1234567890", "Hello WA", agencia=agencia)
        mock_send_wa.assert_called_once()

    def test_telegram_channel_available_with_agency_token(self):
        """Telegram channel available with agency token."""
        agencia = Mock()
        agencia.telegram_bot_token = "123:token"
        agencia.telegram_chat_id = "group123"
        channel = TelegramChannel()
        assert channel.is_available(agencia=agencia) is True

    @patch("apps.common.tasks.send_telegram_task.delay")
    def test_telegram_channel_send_uses_agency_context(self, mock_send_telegram):
        """Telegram channel send uses agency context."""
        agencia = Mock()
        agencia.telegram_bot_token = "123:token"
        agencia.telegram_chat_id = "group123"
        channel = TelegramChannel()
        channel.send("group123", "Hello Telegram", agencia=agencia)
        mock_send_telegram.assert_called_once()
