"""Tests para Ai router (Services)."""
import unittest.mock

import pytest


class TestGeminiRouterInit:
    """Test Gemini Router Init."""
    def test_raises_value_error_when_no_api_key(self, monkeypatch):
        """Raises value error when no api key."""
        monkeypatch.setattr(
            "apps.automation.services.ai_router.get_gemini_api_key",
            lambda agency=None: None,
        )
        from apps.automation.services.ai_router import GeminiRouter

        with pytest.raises(ValueError, match="GEMINI_API_KEY is missing"):
            GeminiRouter()


class TestClassifyEmail:
    @pytest.fixture(autouse=True)
    """Test Classify Email."""
    def _setup_router(self, monkeypatch):
        """Setup router."""
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
        """Classify email returns enum."""
        result = self.router.classify_email("test email content")
        from apps.automation.services.ai_router import EmailType

        assert result == EmailType.TICKET_ISSUANCE

    def test_classify_email_returns_other_on_error(self, monkeypatch):
        """Classify email returns other on error."""
        self.router.client.chat.completions.create.side_effect = Exception("API error")
        from apps.automation.services.ai_router import EmailType

        result = self.router.classify_email("test content")
        assert result == EmailType.OTHER


class TestExtractTicketData:
    @pytest.fixture(autouse=True)
    """Test Extract Ticket Data."""
    def _setup_router(self, monkeypatch):
        """ setup router."""
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
        """Extract ticket data."""
        result = self.router.extract_ticket_data("email content")
        assert result is not None
        assert result.pnr == "ABC123"
        assert result.passenger_name == "TEST"

    def test_extract_ticket_data_returns_none_on_error(self):
        """Extract ticket data returns none on error."""
        self.router.client.chat.completions.create.side_effect = Exception("API error")
        result = self.router.extract_ticket_data("content")
        assert result is None


class TestValidateTicket:
    """Test Validate Ticket."""
    def test_validates_valid_ticket(self):
        """Validates valid ticket."""
        from apps.automation.services.ai_router import TicketSchema, validate_ticket

        ticket = TicketSchema(
            pnr="ABC123",
            passenger_name="TEST",
            itinerary=[],
        )
        assert validate_ticket(ticket) is True

    def test_rejects_none_ticket(self):
        """Rejects none ticket."""
        from apps.automation.services.ai_router import validate_ticket

        assert validate_ticket(None) is False
