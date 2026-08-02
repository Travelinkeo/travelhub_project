from apps.automation.parsers.normalization import DataNormalizationService


def test_kiu_normalized_block_minimal():
    """test_kiu_normalized_block_minimal."""
    raw = {
        "SOURCE_SYSTEM": "KIU",
        "NUMERO_DE_BOLETO": "308-0201196996",
        "CODIGO_RESERVA": "ABC123",
        "NOMBRE_DEL_PASAJERO": "DUQUE/OSCAR",
        "FECHA_DE_EMISION": "17 AUG 2025",
        "TARIFA_IMPORTE": "170.00",
        "TOTAL_IMPORTE": "210.50",
        "TOTAL_MONEDA": "USD",
    }
    n = DataNormalizationService.normalize_ticket_data(raw)
    assert n.get("SOURCE_SYSTEM") == "KIU"
    assert n.get("ticket_number") == "308-0201196996"
    assert n.get("reservation_code") == "ABC123"
    assert n.get("passenger_name") is not None
    assert n.get("fare_amount") == "170.00"
    assert n.get("total_amount") == "210.50"
    assert n.get("total_currency") == "USD"


def test_sabre_normalized_block_minimal():
    """test_sabre_normalized_block_minimal."""
    raw = {
        "SOURCE_SYSTEM": "SABRE",
        "numero_boleto": "3080201196996",
        "codigo_reservacion": "ABC123",
        "preparado_para": "DOE/JOHN",
        "fecha_emision_iso": "2025-08-17",
        "fare_currency": "USD",
        "fare_amount": "123.45",
        "total_currency": "USD",
        "total_amount": "150.60",
    }
    n = DataNormalizationService.normalize_ticket_data(raw)
    assert n.get("SOURCE_SYSTEM") == "SABRE"
    assert n.get("ticket_number") == "3080201196996"
    assert n.get("reservation_code") == "ABC123"
    assert n.get("passenger_name") is not None
    assert n.get("issue_date") == "2025-08-17"
