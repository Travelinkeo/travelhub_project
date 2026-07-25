"""Tests de integración para parsers"""

import pytest

from apps.automation.parsers.adapter import parse_ticket_with_new_parsers


@pytest.mark.django_db
class TestParsersIntegration:
    """Tests de integración para todos los parsers"""

    def test_sabre_detection(self):
        """Sabre detection."""
        text = "ETICKET RECEIPT\nRESERVATION CODE: ABC123\nTicket Number: 1234567890"
        result = parse_ticket_with_new_parsers(text)
        assert result["SOURCE_SYSTEM"] == "SABRE"
        assert "error" not in result

    def test_amadeus_detection(self):
        """Amadeus detection."""
        text = "ELECTRONIC TICKET RECEIPT\nBOOKING REF: XYZ789"
        result = parse_ticket_with_new_parsers(text)
        assert result["SOURCE_SYSTEM"] == "AMADEUS"
        assert "error" not in result

    def test_kiu_detection(self):
        """Kiu detection."""
        text = "KIUSYS.COM\nPASSENGER ITINERARY RECEIPT"
        result = parse_ticket_with_new_parsers(text)
        assert result["SOURCE_SYSTEM"] == "KIU"
        assert "error" not in result

    def test_copa_detection(self):
        """Copa detection."""
        text = "COPA AIRLINES\nLocalizador de reserva ABC123"
        result = parse_ticket_with_new_parsers(text)
        assert result["SOURCE_SYSTEM"] == "COPA_SPRK"
        assert "error" not in result

    def test_wingo_detection(self):
        """Wingo detection."""
        text = "WINGO.COM\nCódigo de reserva XYZ789"
        result = parse_ticket_with_new_parsers(text)
        assert result["SOURCE_SYSTEM"] == "WINGO"
        assert "error" not in result

    def test_travelport_detection(self):
        """Travelport detection."""
        text = "VIEWTRIP\nELECTRONIC TICKET RECEIPT\nTicket Number: 1234567890"
        result = parse_ticket_with_new_parsers(text)
        assert result["SOURCE_SYSTEM"] == "TRAVELPORT"
        assert "error" not in result

    def test_tk_connect_detection(self):
        """Tk connect detection."""
        text = "IDENTIFICACIÓN DEL PEDIDO: XYZ789\nTK CONNECT\nTicket Number: 1234"
        result = parse_ticket_with_new_parsers(text)
        assert result["SOURCE_SYSTEM"] == "TK_CONNECT"
        assert "error" not in result

    def test_unknown_system(self):
        """Unknown system."""
        text = "Random text without any GDS markers"
        result = parse_ticket_with_new_parsers(text)
        assert "error" in result

    def test_pydantic_schema_validation(self):
        """Pydantic schema validation."""
        from apps.automation.parsers.registry import registry
        from core.models.ai_schemas import ResultadoParseoSchema

        # Test Sabre parsing Pydantic generation
        text = "ETICKET RECEIPT\nRESERVATION CODE: ABC123\nTicket Number: 1234567890123\nPrepared For: SMITH/JOHN\nIssue Date: 14MAR26\nIssuing Airline: AMERICAN AIRLINES\nFare: USD 500.00\nTotal: USD 550.00\nTax: USD 50.00"

        # Primero registrar parsers
        parse_ticket_with_new_parsers(text)

        parser = registry.find_parser(text)
        assert parser is not None

        parsed_data = parser.parse(text)
        pydantic_res = parsed_data.to_pydantic()
        assert isinstance(pydantic_res, ResultadoParseoSchema)
        assert len(pydantic_res.boletos) == 1
        assert pydantic_res.boletos[0].nombre_pasajero == "SMITH/JOHN"
        assert pydantic_res.boletos[0].codigo_reserva == "ABC123"
        assert pydantic_res.boletos[0].numero_boleto == "1234567890123"
