import unittest.mock

import pytest


class TestParseTicketWithGemini:
    @pytest.fixture(autouse=True)
    def _mock_generate_content(self, monkeypatch):
        self.mock_generate = unittest.mock.MagicMock()
        monkeypatch.setattr(
            "apps.automation.services.ai_parser.generate_content",
            self.mock_generate,
        )
        return self.mock_generate

    def test_returns_parsed_data_on_success(self):
        from apps.automation.services.ai_parser import parse_ticket_with_gemini

        self.mock_generate.return_value = (
            '{"passenger": {"name": "JUAREZ/RAUL"}, "bookingDetails": {"ticketNumber": "0457281019415"}}'
        )
        result = parse_ticket_with_gemini("ticket text here")
        assert result is not None
        assert result["SOURCE_SYSTEM"] == "GEMINI_AI"
        assert result["normalized"]["passenger"]["name"] == "JUAREZ/RAUL"

    def test_returns_none_on_configuration_error(self):
        from apps.automation.services.ai_parser import parse_ticket_with_gemini
        from apps.automation.services.ai_engine import GeminiConfigurationError

        self.mock_generate.side_effect = GeminiConfigurationError("no key")
        result = parse_ticket_with_gemini("ticket text")
        assert result is None

    def test_returns_none_on_json_decode_error(self):
        from apps.automation.services.ai_parser import parse_ticket_with_gemini

        self.mock_generate.return_value = "not json at all"
        result = parse_ticket_with_gemini("ticket text")
        assert result is None

    def test_returns_none_on_unexpected_exception(self):
        from apps.automation.services.ai_parser import parse_ticket_with_gemini

        self.mock_generate.side_effect = Exception("unexpected")
        result = parse_ticket_with_gemini("ticket text")
        assert result is None
