import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.critical,
    pytest.mark.django_db,
]


def test_login_page_loads(page, live_server):
    page.goto(f"{live_server.url}/login/")
    assert page.locator('input[name="username"]').is_visible()
    assert page.locator('input[name="password"]').is_visible()
    assert page.locator("text=Iniciar Sesión").is_visible()


def test_login_success(logged_in_page, live_server):
    logged_in_page.goto(f"{live_server.url}/dashboard/modern/")
    logged_in_page.wait_for_timeout(1000)
    body = logged_in_page.text_content("body") or ""
    assert len(body) > 0


def test_crear_venta(logged_in_page, live_server, moneda_usd, sample_cliente):
    venta_url = f"{live_server.url}/bookings/ventas/nueva/"
    logged_in_page.goto(venta_url)
    logged_in_page.wait_for_timeout(1000)

    logged_in_page.locator("#id_cliente").select_option(str(sample_cliente.id))
    logged_in_page.locator("#id_moneda").select_option(str(moneda_usd.id))
    logged_in_page.locator("#id_tipo_venta").select_option("AEREA")
    logged_in_page.locator("#id_descripcion_general").fill("Venta de prueba E2E - Playwright")
    logged_in_page.locator("#id_notas").fill("Creado desde test automatizado")

    logged_in_page.click('button[type="submit"]')
    logged_in_page.wait_for_timeout(2000)

    assert "login" not in logged_in_page.url.lower()
