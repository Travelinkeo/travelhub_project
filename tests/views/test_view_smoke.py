"""Pruebas de humo para vistas críticas — status code, template, permisos.

Usa admin_client (superuser autenticado) para verificar que las vistas
principales no fallen con 500 y retornen status aceptables.
"""

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.views]

# URLs que no requieren parámetros dinámicos
SMOKE_URLS = [
    "/dashboard/modern/",
    "/account/billing/",
    "/agencia/usuarios/",
    "/health/",
    "/tools/traductor/",
    "/wiki/gds/",
    "/god-mode/",
    "/ceo-dashboard/",
    "/notifications/live/",
    "/api/docs/",
    "/api/redoc/",
    "/upload/boleto/",
    "/cotizaciones/nueva/",
    "/analytics/sales/",
    "/analytics/finance/",
    "/analytics/ops/",
]


class TestViewSmoke:
    @pytest.mark.parametrize("url", SMOKE_URLS)
    def test_view_returns_valid_status(self, url, admin_client):
        """Verifica que la vista no lance 500."""
        response = admin_client.get(url)
        assert response.status_code not in (500, 404), (
            f"{url} retornó {response.status_code}"
        )

    def test_health_endpoint(self, admin_client):
        response = admin_client.get("/health/")
        assert response.status_code in (200, 302)

    def test_admin_login_page(self, client):
        response = client.get("/admin/login/")
        assert response.status_code == 200

    def test_schema_endpoint(self, admin_client):
        response = admin_client.get("/api/schema/")
        assert response.status_code in (200, 302)

    def test_ceo_dashboard(self, admin_client):
        response = admin_client.get("/ceo-dashboard/")
        assert response.status_code in (200, 302)
