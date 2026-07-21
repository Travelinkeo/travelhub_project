import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.critical,
    pytest.mark.django_db,
]


@pytest.fixture
def venta_con_cliente(db, moneda_usd, sample_cliente):
    from apps.bookings.models import Venta

    venta = Venta.objects.create(
        cliente=sample_cliente,
        moneda=moneda_usd,
        tipo_venta="AEREA",
        estado="ACTIVA",
        descripcion_general="Venta para facturación E2E",
        localizador=f"LOC-{__import__('secrets').token_hex(4).upper()}",
        total_venta=500.00,
    )
    return venta


def test_detalle_venta(logged_in_page, live_server, venta_con_cliente):
    detail_url = f"{live_server.url}/bookings/ventas/{venta_con_cliente.pk}/"
    logged_in_page.goto(detail_url)
    logged_in_page.wait_for_timeout(1000)

    body = logged_in_page.text_content("body") or ""
    assert venta_con_cliente.localizador in body


def test_listado_ventas(logged_in_page, live_server, venta_con_cliente):
    list_url = f"{live_server.url}/bookings/ventas/"
    logged_in_page.goto(list_url)
    logged_in_page.wait_for_timeout(1000)

    body = logged_in_page.text_content("body") or ""
    assert venta_con_cliente.cliente.nombres in body
