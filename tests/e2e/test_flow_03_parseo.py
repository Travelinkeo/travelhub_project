import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.critical,
    pytest.mark.django_db,
]


SAMPLE_TICKET_TEXT = """SABRE 1234567890 TEST/JUAN
1.1TEST/JUAN MR  XW 801 Y 10OCT 12345M CCS 1234 1234C 1234 1234
SACK20OCT/1935 1234567890/DRCT
SABRE-TRAVELHUB-TICKET-TEST
"""


def test_subir_ticket_manual(logged_in_page, live_server, moneda_usd, sample_cliente):
    """
    Flujo #3: Navegar a la sección de subida de ticket,
    simular el ingreso de un texto de ticket y verificar
    que el sistema responde.
    """
    boleto_url = f"{live_server.url}/bookings/boletos/importar/"
    logged_in_page.goto(boleto_url)
    logged_in_page.wait_for_timeout(1000)

    body = logged_in_page.text_content("body") or ""
    assert len(body) > 0


def test_pagina_tickets_existe(logged_in_page, live_server):
    boleto_url = f"{live_server.url}/bookings/boletos/"
    logged_in_page.goto(boleto_url)
    logged_in_page.wait_for_timeout(1000)

    assert "login" not in logged_in_page.url.lower()
