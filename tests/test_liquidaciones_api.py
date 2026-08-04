# tests/test_liquidaciones_api.py
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.bookings.models import Proveedor, Venta
from apps.common.models import Moneda
from apps.contabilidad.models import LiquidacionProveedor
from apps.crm.models import Cliente

pytestmark = pytest.mark.skip(
    reason="No existe ViewSet REST para /api/liquidaciones/. Solo existe LiquidacionDashboardView (TemplateView en apps/finance/views/liquidaciones_views.py). Se necesita crear LiquidacionViewSet + router.register() en urls_api.py. Verificado 2026-08-03."
)

User = get_user_model()


@pytest.fixture
def api_client():
    """api_client."""
    return APIClient()


@pytest.fixture
def user(db):
    """user."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def authenticated_client(api_client, user):
    """authenticated_client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def proveedor(db):
    """proveedor."""
    return Proveedor.objects.create(nombre="Proveedor Test", tipo_proveedor="MAY")


@pytest.fixture
def moneda_usd(db):
    """moneda_usd."""
    return Moneda.objects.get_or_create(codigo_iso="USD", defaults={"nombre": "Dólar"})[0]


@pytest.fixture
def cliente(db):
    """cliente."""
    return Cliente.objects.create(nombres="Test", apellidos="Cliente")


@pytest.fixture
def venta(db, cliente, moneda_usd, user):
    """venta."""
    return Venta.objects.create(cliente=cliente, moneda=moneda_usd, subtotal=1000, creado_por=user)


@pytest.fixture
def liquidacion(db, proveedor, venta):
    """liquidacion."""
    return LiquidacionProveedor.objects.create(
        proveedor=proveedor, venta=venta, monto_total=Decimal("500.00")
    )


@pytest.mark.django_db
class TestLiquidacionesAPI:
    """TestLiquidacionesAPI."""

    def test_listar_liquidaciones(self, authenticated_client, liquidacion):
        """test_listar_liquidaciones."""
        response = authenticated_client.get("/api/liquidaciones/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filtrar_por_estado(self, authenticated_client, liquidacion):
        """test_filtrar_por_estado."""
        response = authenticated_client.get("/api/liquidaciones/?estado=PEN")
        assert response.status_code == 200

    def test_marcar_pagada(self, authenticated_client, liquidacion):
        """test_marcar_pagada."""
        response = authenticated_client.post(
            f"/api/liquidaciones/{liquidacion.id_liquidacion}/marcar_pagada/"
        )
        assert response.status_code == 200

        liquidacion.refresh_from_db()
        assert liquidacion.estado == "PAG"
        assert liquidacion.saldo_pendiente == 0

    def test_pago_parcial(self, authenticated_client, liquidacion):
        """test_pago_parcial."""
        response = authenticated_client.post(
            f"/api/liquidaciones/{liquidacion.id_liquidacion}/registrar_pago_parcial/",
            {"monto": 200.00},
            format="json",
        )
        assert response.status_code == 200

        liquidacion.refresh_from_db()
        assert liquidacion.estado == "PAR"
        assert liquidacion.saldo_pendiente == Decimal("300.00")

    def test_pago_parcial_excede_saldo(self, authenticated_client, liquidacion):
        """test_pago_parcial_excede_saldo."""
        response = authenticated_client.post(
            f"/api/liquidaciones/{liquidacion.id_liquidacion}/registrar_pago_parcial/",
            {"monto": 600.00},
            format="json",
        )
        assert response.status_code == 400

    def test_liquidaciones_pendientes(self, authenticated_client, liquidacion):
        """test_liquidaciones_pendientes."""
        response = authenticated_client.get("/api/liquidaciones/pendientes/")
        assert response.status_code == 200
        assert len(response.data) == 1
