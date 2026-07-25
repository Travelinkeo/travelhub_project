"""Fixtures compartidos para tests E2E con Playwright — usuarios, monedas, clientes y página autenticada."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configura el locale español para el navegador en tests E2E."""
    return {**browser_context_args, "locale": "es-ES"}


@pytest.fixture
def page(page):
    """Configura viewport de 1440x900 para las páginas E2E."""
    page.set_viewport_size({"width": 1440, "height": 900})
    return page


@pytest.fixture
def test_password():
    """Contraseña estándar para usuarios E2E."""
    return "E2ePass1!"


@pytest.fixture
def e2e_user(db, test_password):
    """Crea un usuario staff para tests E2E. Args: db, test_password. Returns: User."""
    user = User.objects.create_user(
        username="e2e_tester",
        email="e2e@travelhub.cc",
        password=test_password,
        is_staff=True,
        is_active=True,
    )
    return user


@pytest.fixture
def moneda_usd(db):
    """Crea moneda USD para tests E2E. Args: db. Returns: Moneda."""
    from apps.common.models import Moneda

    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="USD",
        defaults={"nombre": "Dólar", "simbolo": "$", "activa": True},
    )
    return moneda


@pytest.fixture
def moneda_ves(db):
    """Crea moneda VES para tests E2E. Args: db. Returns: Moneda."""
    from apps.common.models import Moneda

    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="VES",
        defaults={"nombre": "Bolívar", "simbolo": "Bs.", "activa": True},
    )
    return moneda


@pytest.fixture
def sample_cliente(db):
    """Crea un cliente de ejemplo para tests E2E. Args: db. Returns: Cliente."""
    from apps.crm.models import Cliente

    cliente = Cliente.objects.create(
        tipo_documento="V",
        documento_identidad="12345678",
        nombres="María",
        apellidos="González",
        email="maria@test.com",
        telefono="+584141234567",
    )
    return cliente


@pytest.fixture
def sample_cliente_2(db):
    """Crea un segundo cliente de ejemplo para tests E2E. Args: db. Returns: Cliente."""
    from apps.crm.models import Cliente

    cliente = Cliente.objects.create(
        tipo_documento="V",
        documento_identidad="87654321",
        nombres="Carlos",
        apellidos="López",
        email="carlos@test.com",
        telefono="+584129876543",
    )
    return cliente


@pytest.fixture
def logged_in_page(page, live_server, e2e_user, test_password):
    """Autentica la página Playwright con el usuario E2E. Args: page, live_server, e2e_user, test_password. Returns: Page."""
    page.goto(f"{live_server.url}/login/")
    page.fill('input[name="username"]', e2e_user.username)
    page.fill('input[name="password"]', test_password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(1500)
    return page
