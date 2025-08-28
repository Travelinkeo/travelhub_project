import re
import pytest
from core.pdf_generator import generate_ticket_pdf
from core.utils import LOCATION_TOKENS

@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_name,expected",
    [
        ("DUQUE ECHEVERRY/OSCA FLORIDA", "DUQUE ECHEVERRY/OSCA"),
        ("PEREZ/ANA CIUDAD DE PANAMA PANAMA", "PEREZ/ANA"),
        ("ROJAS/EMMA UNITED STATES", "ROJAS/EMMA"),
        ("GONZALEZ/JOSE (CIUDAD DE PANAMA) (PANAMA)", "GONZALEZ/JOSE"),
    ],
)
def test_pdf_generator_passenger_name_sanitization(raw_name, expected):
    data = {
        'SOURCE_SYSTEM': 'KIU',
        'NOMBRE_DEL_PASAJERO': raw_name,
        'NUMERO_DE_BOLETO': '1234567890',
        'FECHA_DE_EMISION': '01 JAN 2025',
        'AGENTE_EMISOR': 'AGT01',
        'NOMBRE_AEROLINEA': 'TEST AIRLINE',
        'DIRECCION_AEROLINEA': 'ADDRESS 123',
        'SOLO_NOMBRE_PASAJERO': raw_name.split('/')[1] if '/' in raw_name else raw_name,
        'SOLO_CODIGO_RESERVA': 'ABC123',
        'CODIGO_IDENTIFICACION': 'ID123',
        'ItinerarioFinalLimpio': 'CCS BOG 01JAN'
    }
    pdf_bytes, filename = generate_ticket_pdf(data)

    # El filename actualmente NO incluye el nombre, así que validamos el efecto indirecto:
    # 1. La función debe haber mutado data['NOMBRE_DEL_PASAJERO'] a la versión saneada.
    assert data['NOMBRE_DEL_PASAJERO'] == expected, (
        f"Nombre no saneado como se esperaba. Original: {raw_name} -> Actual: {data['NOMBRE_DEL_PASAJERO']} "
        f"Esperado: {expected}"
    )
    # 2. PDF debe tener contenido no vacío razonable
    assert len(pdf_bytes) > 1000, "PDF demasiado pequeño: posible fallo render"
