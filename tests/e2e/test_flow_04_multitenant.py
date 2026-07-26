import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.critical,
    pytest.mark.django_db,
]


@pytest.fixture
def agencia_a(db):
    """agencia_a."""
    from core.models.agencia import Agencia

    agencia, _ = Agencia.objects.get_or_create(
        nombre="Agencia A E2E",
        defaults={
            "rif": "J-12345678-0",
            "dominio": "agencia-a-e2e",
            "plan": "premium",
            "activa": True,
        },
    )
    return agencia


@pytest.fixture
def agencia_b(db):
    """agencia_b."""
    from core.models.agencia import Agencia

    agencia, _ = Agencia.objects.get_or_create(
        nombre="Agencia B E2E",
        defaults={
            "rif": "J-87654321-0",
            "dominio": "agencia-b-e2e",
            "plan": "basico",
            "activa": True,
        },
    )
    return agencia


@pytest.fixture
def user_agencia_a(db, agencia_a):
    """user_agencia_a."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="user_a_e2e",
        email="agencia_a@test.com",
        password="TestPass1!",
        is_staff=True,
    )
    user.agencia = agencia_a
    user.save(update_fields=["agencia"])
    return user


@pytest.fixture
def user_agencia_b(db, agencia_b):
    """user_agencia_b."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.create_user(
        username="user_b_e2e",
        email="agencia_b@test.com",
        password="TestPass2!",
        is_staff=True,
    )
    user.agencia = agencia_b
    user.save(update_fields=["agencia"])
    return user


@pytest.fixture
def venta_agencia_a(db, agencia_a, moneda_usd, sample_cliente):
    """venta_agencia_a."""
    from apps.bookings.models import Venta

    venta = Venta.objects.create(
        agencia=agencia_a,
        cliente=sample_cliente,
        moneda=moneda_usd,
        tipo_venta="AEREA",
        estado="ACTIVA",
        descripcion_general="Venta Agencia A",
        localizador=f"LOC-A-{__import__('secrets').token_hex(4).upper()}",
        total_venta=1000.00,
    )
    return venta


def test_multi_tenancy_aislamiento(
    page,
    live_server,
    db,
    user_agencia_a,
    user_agencia_b,
    venta_agencia_a,
):
    """
    Verifica que el usuario de Agencia B NO puede ver
    las ventas de Agencia A en el listado.
    """
    login_url = f"{live_server.url}/login/"

    page.goto(login_url)
    page.fill('input[name="username"]', user_agencia_b.username)
    page.fill('input[name="password"]', "TestPass2!")
    page.click('button[type="submit"]')
    page.wait_for_timeout(1500)

    ventas_url = f"{live_server.url}/bookings/ventas/"
    page.goto(ventas_url)
    page.wait_for_timeout(1000)

    body = page.text_content("body") or ""
    assert venta_agencia_a.localizador not in body, "Agencia B no debería ver ventas de Agencia A"
