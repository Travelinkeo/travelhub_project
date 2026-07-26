import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """browser_context_args."""
    return {**browser_context_args, "locale": "es-ES"}


@pytest.fixture
def page(page):
    """page."""
    page.set_viewport_size({"width": 1440, "height": 900})
    return page


@pytest.fixture
def test_password():
    """test_password."""
    return "E2ePass1!"


@pytest.fixture
def e2e_user(db, test_password):
    """e2e_user."""
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
    """moneda_usd."""
    from apps.common.models import Moneda

    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="USD",
        defaults={"nombre": "Dólar", "simbolo": "$", "activa": True},
    )
    return moneda


@pytest.fixture
def moneda_ves(db):
    """moneda_ves."""
    from apps.common.models import Moneda

    moneda, _ = Moneda.objects.get_or_create(
        codigo_iso="VES",
        defaults={"nombre": "Bolívar", "simbolo": "Bs.", "activa": True},
    )
    return moneda


@pytest.fixture
def sample_cliente(db):
    """sample_cliente."""
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
    """sample_cliente_2."""
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
    """logged_in_page."""
    page.goto(f"{live_server.url}/login/")
    page.fill('input[name="username"]', e2e_user.username)
    page.fill('input[name="password"]', test_password)
    page.click('button[type="submit"]')
    page.wait_for_timeout(1500)
    return page
