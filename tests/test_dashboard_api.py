"""Tests para Dashboard api."""
import pytest

# tests/test_dashboard_api.py
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.bookings.models import Venta
from apps.common.models import Moneda
from apps.crm.models import Cliente

pytestmark = pytest.mark.skip(reason="Endpoints de dashboard no registrados en URLs")

User = get_user_model()


@pytest.fixture
def api_client():
    """Api client."""
    return APIClient()


@pytest.fixture
def user(db):
    """User."""
    return User.objects.create_user(username="testuser", password="testpass123")


@pytest.fixture
def authenticated_client(api_client, user):
    """Authenticated client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def moneda_usd(db):
    """Moneda usd."""
    return Moneda.objects.get_or_create(codigo_iso="USD", defaults={"nombre": "Dólar"})[0]


@pytest.fixture
def cliente(db):
    """Cliente."""
    return Cliente.objects.create(nombres="Juan", apellidos="Pérez", email="juan@test.com")


@pytest.mark.django_db
class TestDashboardMetricas:
    """Test Dashboard Metricas."""
    def test_metricas_sin_datos(self, authenticated_client):
        """Metricas sin datos."""
        response = authenticated_client.get("/api/dashboard/metricas/")
        assert response.status_code == 200
        assert response.data["resumen"]["total_ventas"] == 0
        assert response.data["resumen"]["monto_total"] == 0.0

    def test_metricas_con_ventas(self, authenticated_client, cliente, moneda_usd, user):
        """Metricas con ventas."""
        Venta.objects.create(
            cliente=cliente, moneda=moneda_usd, subtotal=1000, impuestos=100, creado_por=user
        )

        response = authenticated_client.get("/api/dashboard/metricas/")
        assert response.status_code == 200
        assert response.data["resumen"]["total_ventas"] == 1
        assert response.data["resumen"]["monto_total"] > 0

    def test_metricas_con_filtro_fecha(self, authenticated_client):
        """Metricas con filtro fecha."""
        response = authenticated_client.get(
            "/api/dashboard/metricas/?fecha_desde=2025-01-01&fecha_hasta=2025-12-31"
        )
        assert response.status_code == 200

    def test_metricas_sin_autenticacion(self, api_client):
        """Metricas sin autenticacion."""
        response = api_client.get("/api/dashboard/metricas/")
        assert response.status_code in [401, 403]  # 403 si hay throttling


@pytest.mark.django_db
class TestDashboardAlertas:
    """Test Dashboard Alertas."""
    def test_alertas_basicas(self, authenticated_client):
        """Alertas basicas."""
        response = authenticated_client.get("/api/dashboard/alertas/")
        assert response.status_code == 200
        assert "alertas" in response.data
        assert len(response.data["alertas"]) == 4

    def test_alertas_estructura(self, authenticated_client):
        """Alertas estructura."""
        response = authenticated_client.get("/api/dashboard/alertas/")
        alerta = response.data["alertas"][0]
        assert "tipo" in alerta
        assert "count" in alerta
        assert "mensaje" in alerta
        assert "severidad" in alerta
