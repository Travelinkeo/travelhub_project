"""Tests para servicios unificados de email"""

from unittest.mock import MagicMock, Mock, patch

from apps.communications.services.email_unified import (
    EmailMonitorService,
    enviar_email_generico,
    send_custom_email,
)


class TestEmailUnified:
    """Tests para email unified service"""

    @patch("apps.communications.services.email_unified.render_to_string")
    @patch("apps.communications.services.email_unified.resend.Emails.send")
    def test_send_custom_email_resend_success(self, mock_resend, mock_render, settings):
        settings.RESEND_API_KEY = "test_key"
        mock_render.return_value = "<html>Test</html>"

        result = send_custom_email("Test Subject", "test@example.com", "test_template.html", {})

        assert result is True
        mock_resend.assert_called_once()

    @patch("apps.communications.services.email_unified.render_to_string")
    @patch("apps.communications.services.email_unified.send_mail")
    def test_send_custom_email_django_fallback(self, mock_send, mock_render, settings):
        import apps.communications.services.email_unified as email_mod

        original_key = email_mod.RESEND_API_KEY
        email_mod.RESEND_API_KEY = None
        try:
            mock_render.return_value = "<html>Test</html>"
            result = send_custom_email("Test Subject", "test@example.com", "test_template.html", {})
            assert result is True
            mock_send.assert_called_once()
        finally:
            email_mod.RESEND_API_KEY = original_key

    def test_send_custom_email_no_recipient(self):
        result = send_custom_email("Test", None, "template.html", {})
        assert result is False

    @patch("apps.communications.services.email_unified.EmailMultiAlternatives")
    def test_enviar_email_generico_success(self, mock_email_class):
        mock_email = Mock()
        mock_email_class.return_value = mock_email

        result = enviar_email_generico("test@example.com", "Subject", "Message")

        assert result is True
        mock_email.send.assert_called_once()

    @patch("apps.communications.services.email_unified.EmailMultiAlternatives")
    def test_enviar_email_generico_failure(self, mock_email_class):
        mock_email_class.side_effect = Exception("SMTP error")

        result = enviar_email_generico("test@example.com", "Subject", "Message")

        assert result is False


class TestEmailMonitorService:
    """Tests para EmailMonitorService"""

    def test_init_default_values(self):
        agencia = Mock()
        agencia.correo_emisiones = "test@example.com"
        agencia.password_app_correo = "password"
        agencia.whatsapp = None
        agencia.email_ventas = None

        service = EmailMonitorService(agencia)

        assert service.notification_type == "whatsapp"
        assert service.interval == 60
        assert service.mark_as_read is False
        assert service.process_all is False

    def test_init_custom_values(self):
        agencia = Mock()
        agencia.correo_emisiones = "test@example.com"
        agencia.password_app_correo = "password"
        agencia.whatsapp = "+1234567890"
        agencia.email_ventas = None

        service = EmailMonitorService(
            agencia,
            notification_type="email",
            destination="admin@example.com",
            interval=120,
            mark_as_read=True,
            process_all=True,
        )

        assert service.notification_type == "email"
        assert service.destination == "admin@example.com"
        assert service.interval == 120
        assert service.mark_as_read is True
        assert service.process_all is True

    def test_procesar_una_vez_no_credentials(self):
        agencia = Mock()
        agencia.correo_emisiones = None
        agencia.password_app_correo = None
        agencia.nombre = "Test Agency"

        service = EmailMonitorService(agencia)
        result = service.procesar_una_vez()

        assert result == 0

    @patch("apps.communications.services.email_unified.imaplib.IMAP4_SSL")
    def test_procesar_correos_dynamic_host_port(self, mock_imap_ssl):
        agencia = Mock()
        agencia.correo_emisiones = "test@example.com"
        agencia.password_app_correo = "password"
        agencia.nombre = "Test Agency"

        # Configure a custom IMAP host and port in agency configuration
        config = Mock()
        config.email_monitor_host = "imap.custom.com"
        config.email_monitor_port = 995
        agencia.configuracion = config

        # Mock IMAP connection setup
        mock_mail = MagicMock()
        mock_imap_ssl.return_value = mock_mail
        mock_mail.search.return_value = (
            "OK",
            [b""],
        )  # Empty list of messages to stop processing early

        service = EmailMonitorService(agencia)
        service._procesar_correos()

        # Check if IMAP4_SSL was called with the custom host and port
        mock_imap_ssl.assert_called_once_with("imap.custom.com", 995)

    @patch("apps.communications.services.email_unified.imaplib.IMAP4_SSL")
    def test_procesar_correos_fallback_host_port(self, mock_imap_ssl):
        agencia = Mock()
        agencia.correo_emisiones = "test@example.com"
        agencia.password_app_correo = "password"
        agencia.nombre = "Test Agency"

        # Configure configuration to be None or empty
        agencia.configuracion = None

        # Mock IMAP connection setup
        mock_mail = MagicMock()
        mock_imap_ssl.return_value = mock_mail
        mock_mail.search.return_value = ("OK", [b""])

        service = EmailMonitorService(agencia)
        service._procesar_correos()

        # Check if IMAP4_SSL was called with default values (imap.gmail.com, 993)
        mock_imap_ssl.assert_called_once_with("imap.gmail.com", 993)

    def test_tiene_pdf_adjunto_no_multipart(self):
        agencia = Mock()
        agencia.correo_emisiones = "test@example.com"
        agencia.password_app_correo = "password"
        service = EmailMonitorService(agencia)

        message = Mock()
        message.is_multipart.return_value = False

        result = service._tiene_pdf_adjunto(message)
        assert result is False

    def test_extraer_texto_no_multipart(self):
        agencia = Mock()
        agencia.correo_emisiones = "test@example.com"
        agencia.password_app_correo = "password"
        service = EmailMonitorService(agencia)

        message = Mock()
        message.is_multipart.return_value = False
        message.get_payload.return_value = b"Test text content"

        result = service._extraer_texto(message)
        assert result == "Test text content"

    def test_extraer_html_no_multipart_not_html(self):
        agencia = Mock()
        agencia.correo_emisiones = "test@example.com"
        agencia.password_app_correo = "password"
        service = EmailMonitorService(agencia)

        message = Mock()
        message.is_multipart.return_value = False
        message.get_payload.return_value = b"Plain text only"

        result = service._extraer_html(message)
        assert result is None

    @patch("apps.communications.services.email_unified.pypdf.PdfReader")
    def test_es_pdf_boleto_valido_success(self, mock_pdf_reader):
        # Configurar el lector simulado para retornar texto con palabras clave fuertes y de soporte
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "PASSENGER ITINERARY RECORD PNR: ASD123"

        mock_reader_inst = MagicMock()
        mock_reader_inst.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_inst

        agencia = Mock()
        service = EmailMonitorService(agencia)

        assert service._es_pdf_boleto_valido(b"somepdfcontent", "ticket.pdf") is True

    @patch("apps.communications.services.email_unified.pypdf.PdfReader")
    def test_es_pdf_boleto_valido_noise(self, mock_pdf_reader):
        # Configurar el lector para retornar texto sin palabras clave de boletos
        mock_page = MagicMock()
        mock_page.extract_text.return_value = (
            "This is a invoice billing document for monthly subscription of service."
        )

        mock_reader_inst = MagicMock()
        mock_reader_inst.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader_inst

        agencia = Mock()
        service = EmailMonitorService(agencia)

        assert service._es_pdf_boleto_valido(b"somepdfcontent", "invoice.pdf") is False

    @patch("apps.communications.services.email_unified.EmailMonitorService._es_pdf_boleto_valido")
    @patch("apps.bookings.models.BoletoImportado")
    def test_procesar_boleto_pdf_skips_noise(self, mock_boleto_class, mock_es_pdf_valido):
        # Configurar el filtro anti-ruido para retornar False
        mock_es_pdf_valido.return_value = False

        agencia = Mock()
        service = EmailMonitorService(agencia)

        # Simular mensaje con adjunto PDF
        message = Mock()
        message.is_multipart.return_value = True

        # Simular extraer_adjuntos_pdf para que retorne un PDF
        service._extraer_adjuntos_pdf = Mock(return_value=[("invoice.pdf", b"invoicecontent")])

        result = service._procesar_boleto_pdf(message, "123", None)

        # Verificaciones
        assert result is False  # Omitido, procesados_exito = 0
        mock_boleto_class.assert_not_called()  # No se debe guardar
