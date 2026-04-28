import unittest
from unittest.mock import patch

from core.ticket_parser import extract_data_from_text

# Texto de un boleto Sabre de ejemplo para pruebas de fallback
SAMPLE_SABRE_TICKET = '''
ETICKET RECEIPT
PREPARED FOR
DOE/JOHN
RESERVATION CODE: R2D2C3
TICKET NUMBER: 1234567890123
ITINERARY DETAILS
22 MAY 25 AEROVIAS AV 46
DEPARTURE: BOGOTA 07:00
ARRIVAL: MADRID 23:30
'''

# Respuesta de IA simulada y válida
MOCK_AI_RESPONSE = {
    "documentTitle": "E-TICKET RECEIPT",
    "passenger": {"name": "DOE/JOHN", "customerNumber": "N/A"},
    "bookingDetails": {
        "reservationCode": "AI-R2D2",
        "issueDate": "2025-05-08",
        "ticketNumber": "9876543210987",
        "issuingAirline": "AI AIR"
    },
    "flights": [
        {
            "date": "2025-05-22",
            "airline": "AI AIR",
            "flightNumber": "AI 123",
            "departure": {"location": "AI-DEPART", "time": "10:00"},
            "arrival": {"location": "AI-ARRIVE", "time": "12:00"},
            "details": {}
        }
    ]
}

class TestHybridParser(unittest.TestCase):

    @patch('core.ticket_parser.parse_ticket_with_gemini')
    def test_ai_first_strategy_success(self, mock_parse_with_gemini):
        """
        Verifica que si la IA devuelve un resultado válido, se utiliza ese resultado.
        """
        mock_parse_with_gemini.return_value = MOCK_AI_RESPONSE

        result = extract_data_from_text("Cualquier texto de boleto")

        mock_parse_with_gemini.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.get('SOURCE_SYSTEM'), 'GEMINI_AI')
        self.assertIn('normalized', result)
        self.assertEqual(result['normalized']['ticket_number'], '9876543210987')
        self.assertEqual(result['normalized']['source_system'], 'GEMINI_AI')

    @patch('core.ticket_parser.parse_ticket_with_gemini')
    def test_ai_first_strategy_fallback_on_invalid_data(self, mock_parse_with_gemini):
        """
        Verifica que si la IA devuelve datos inválidos, se usa el parser de regex.
        """
        invalid_ai_response = {"passenger": {"name": "Test"}} # Faltan flights y bookingDetails
        mock_parse_with_gemini.return_value = invalid_ai_response

        result = extract_data_from_text(SAMPLE_SABRE_TICKET)

        mock_parse_with_gemini.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.get('SOURCE_SYSTEM'), 'SABRE')
        self.assertIn('normalized', result)
        self.assertEqual(result['normalized']['ticket_number'], '1234567890123')
        self.assertEqual(result['normalized']['source_system'], 'SABRE')

    @patch('core.ticket_parser.parse_ticket_with_gemini')
    def test_ai_first_strategy_fallback_on_ai_failure(self, mock_parse_with_gemini):
        """
        Verifica que si el parser de IA falla (lanza excepción), se usa el parser de regex.
        """
        mock_parse_with_gemini.side_effect = Exception("Fallo de API")

        result = extract_data_from_text(SAMPLE_SABRE_TICKET)

        mock_parse_with_gemini.assert_called_once()
        self.assertIsNotNone(result)
        self.assertEqual(result.get('SOURCE_SYSTEM'), 'SABRE')
        self.assertIn('normalized', result)
        self.assertEqual(result['normalized']['ticket_number'], '1234567890123')

if __name__ == '__main__':
    unittest.main()
