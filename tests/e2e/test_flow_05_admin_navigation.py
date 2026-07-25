"""
E2E: Navegación básica del admin.

Requiere: pytest-playwright, live_server, browser.
Ejecutar: pytest tests/e2e/ -m e2e --headed --ds=travelhub.settings.testing

En CI se ejecuta automáticamente en branches main/staging.
En local requiere:
  1. pip install pytest-playwright
  2. playwright install chromium
  3. PostgreSQL y Redis accesibles
"""

import os

import pytest

pytestmark = [pytest.mark.e2e]

# Saltar si no estamos en CI o si no hay live_server configurado
_e2e_available = os.environ.get("CI") == "true" or os.environ.get("E2E_TESTS") == "1"


class TestAdminNavigation:
    @pytest.mark.skipif(
        """Test Admin Navigation."""
        not _e2e_available,
        reason="E2E tests requieren CI=1 o E2E_TESTS=1 para ejecutarse localmente",
    )
    async def test_admin_login_page(self, page, live_server):
        """Admin login page."""
        await page.goto(f"{live_server.url}/admin/login/")
        content = await page.content()
        assert "admin" in content.lower() or "iniciar" in content.lower()

    @pytest.mark.skipif(
        not _e2e_available,
        reason="E2E tests requieren CI=1 o E2E_TESTS=1",
    )
    async def test_health_page_accessible(self, page, live_server):
        """Health page accessible."""
        await page.goto(f"{live_server.url}/health/")
        content = await page.content()
        assert "ok" in content.lower() or "health" in content.lower()
