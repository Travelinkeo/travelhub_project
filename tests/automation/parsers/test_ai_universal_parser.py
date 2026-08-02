"""Tests para AI Universal Parser."""

import pytest

from apps.automation.parsers.ai_universal_parser import UniversalAIParser


@pytest.fixture
def ai_parser():
    return UniversalAIParser()


@pytest.mark.unit
class TestAIUniversalParserDetection:
    def test_is_fallback_parser(self, ai_parser):
        # Universal parser es el fallback: no tiene can_parse restrictivo
        assert not hasattr(ai_parser, "can_parse") or ai_parser.can_parse("ANY TEXT") is True


@pytest.mark.unit
class TestAIUniversalParserMapping:
    def test_map_to_internal_format(self, ai_parser):
        boleto = {
            "codigo_reserva": "ABC123",
            "numero_boleto": "1234567890123",
            "nombre_pasajero": "PEREZ/JUAN",
            "solo_nombre_pasajero": "JUAN",
            "itinerario": [
                {
                    "aerolinea": "AVIANCA",
                    "numero_vuelo": "AV46",
                    "origen": "CARACAS",
                    "destino": "MADRID",
                }
            ],
        }
        mapped = ai_parser._map_to_internal_format(boleto)
        assert mapped["NOMBRE_DEL_PASAJERO"] == "PEREZ/JUAN"
        assert mapped["CODIGO_RESERVA"] == "ABC123"
        assert mapped["itinerario"][0]["numero_vuelo"] == "AV46"
