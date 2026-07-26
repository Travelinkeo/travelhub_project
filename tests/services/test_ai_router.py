import unittest.mock

import pytest


class TestGeminiRouterInit:
    """TestGeminiRouterInit."""

    def test_raises_value_error_when_no_api_key(self, monkeypatch):
        """test_raises_value_error_when_no_api_key."""
        monkeypatch.setattr(
            "apps.automation.services.ai_router.get_gemini_api_key",
            lambda agency=None: None,
        )
        from apps.automation.services.ai_router import GeminiRouter

        with pytest.raises(ValueError, match="GEMINI_API_KEY is missing"):
            GeminiRouter()


class TestClassifyEmail:
    """TestClassifyEmail."""

    @pytest.fixture(autouse=True)
    def _setup_router(self, monkeypatch):
        """_setup_router."""
        mock_client = unittest.mock.MagicMock()
        mock_completion = unittest.mock.MagicMock()
        mock_completion.choices = [
            unittest.mock.MagicMock(message=unittest.mock.MagicMock(content="ticket_issuance"))
        ]
        mock_client.chat = unittest.mock.MagicMock()
        mock_client.chat.completions = unittest.mock.MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        monkeypatch.setattr(
            "apps.automation.services.ai_router.get_gemini_api_key",
            lambda agency=None: "fake-key",
        )
        monkeypatch.setattr("google.genai.Client", lambda **kwargs: mock_client)
        monkeypatch.setattr("instructor.from_gemini", lambda client, mode: client)

        from apps.automation.services.ai_router import GeminiRouter

        self.router = GeminiRouter()

    def test_classify_email_returns_enum(self, monkeypatch):
        """test_classify_email_returns_enum."""
        result = self.router.classify_email("test email content")
        from apps.automation.services.ai_router import EmailType

        assert result == EmailType.TICKET_ISSUANCE

    def test_classify_email_returns_other_on_error(self, monkeypatch):
        """test_classify_email_returns_other_on_error."""
        self.router.client.chat.completions.create.side_effect = Exception("API error")
        from apps.automation.services.ai_router import EmailType

        result = self.router.classify_email("test content")
        assert result == EmailType.OTHER


class TestExtractTicketData:
    """TestExtractTicketData."""

    @pytest.fixture(autouse=True)
    def _setup_router(self, monkeypatch):
        """_setup_router."""
        mock_client = unittest.mock.MagicMock()
        mock_completion = unittest.mock.MagicMock()
        mock_completion.choices = [
            unittest.mock.MagicMock(
                message=unittest.mock.MagicMock(
                    content='{"pnr": "ABC123", "passenger_name": "TEST", "itinerary": []}'
                )
            )
        ]
        mock_client.chat = unittest.mock.MagicMock()
        mock_client.chat.completions = unittest.mock.MagicMock()
        mock_client.chat.completions.create.return_value = mock_completion

        monkeypatch.setattr(
            "apps.automation.services.ai_router.get_gemini_api_key",
            lambda agency=None: "fake-key",
        )
        monkeypatch.setattr("google.genai.Client", lambda **kwargs: mock_client)
        monkeypatch.setattr("instructor.from_gemini", lambda client, mode: client)

        from apps.automation.services.ai_router import GeminiRouter

        self.router = GeminiRouter()

    def test_extract_ticket_data(self):
        """test_extract_ticket_data."""
        result = self.router.extract_ticket_data("email content")
        assert result is not None
        assert result.pnr == "ABC123"
        assert result.passenger_name == "TEST"

    def test_extract_ticket_data_returns_none_on_error(self):
        """test_extract_ticket_data_returns_none_on_error."""
        self.router.client.chat.completions.create.side_effect = Exception("API error")
        result = self.router.extract_ticket_data("content")
        assert result is None


class TestValidateTicket:
    """TestValidateTicket."""

    def test_validates_valid_ticket(self):
        """test_validates_valid_ticket."""
        from apps.automation.services.ai_router import TicketSchema, validate_ticket

        ticket = TicketSchema(
            pnr="ABC123",
            passenger_name="TEST",
            itinerary=[],
        )
        assert validate_ticket(ticket) is True

    def test_rejects_none_ticket(self):
        """test_rejects_none_ticket."""
        from apps.automation.services.ai_router import validate_ticket

        assert validate_ticket(None) is False
