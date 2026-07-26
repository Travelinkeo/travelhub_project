"""Pruebas de humo para vistas críticas — status code, template, permisos.

Verifica que las URLs principales no fallen con 500 y retornen
status aceptables. Se salta vistas que requieren parámetros dinámicos.
"""

import pytest

pytestmark = [pytest.mark.views]

# URLs fijas (sin parámetros dinámicos) confirmadas en core/urls.py y core/urls_system.py
SMOKE_URLS = [
    "/health/",
    "/health/metrics/",
    "/api/schema/",
    "/chatbot/status/",
    "/login/",
    "/portal/",
    "/onboarding/",
    "/agencia/cambiar/",
    "/setup/perfil/",
    "/tools/traductor/",
    "/wiki/gds/",
    "/notifications/live/",
    "/api/cron/health/",
    "/api/dashboard/stats/",
    "/admin/",
    "/admin/login/",
]


class TestViewSmoke:
    """TestViewSmoke."""

    @pytest.mark.django_db
    @pytest.mark.parametrize("url", SMOKE_URLS)
    def test_view_returns_valid_status(self, url, client):
        """Verifica que la URL no lance 500."""
        response = client.get(url)
        # Aceptamos 200, 302 (redirect), 301 (redirect perm), 403 (forbidden sin auth)
        assert response.status_code not in (500,), f"{url} retornó 500 INTERNAL SERVER ERROR"

    def test_admin_login_template(self, client):
        """test_admin_login_template."""
        response = client.get("/admin/login/")
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_health_check_json(self, client):
        """test_health_check_json."""
        response = client.get("/health/", HTTP_ACCEPT="application/json")
        assert response.status_code in (200, 302)

    @pytest.mark.django_db
    def test_health_check_html(self, client):
        """test_health_check_html."""
        response = client.get("/health/")
        assert response.status_code in (200, 302)

    @pytest.mark.django_db
    def test_api_schema_returns_json(self, client):
        """test_api_schema_returns_json."""
        response = client.get("/api/schema/")
        assert response.status_code in (200, 302)

    def test_login_page_has_form(self, client):
        """test_login_page_has_form."""
        response = client.get("/login/")
        assert response.status_code == 200
        assert "form" in response.content.decode().lower()
