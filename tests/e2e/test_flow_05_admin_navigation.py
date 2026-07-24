"""
E2E: Navegación básica del admin.

Requiere: pytest-playwright, live_server, browser.
Ejecutar: pytest tests/e2e/ -m e2e --headed
"""

import pytest

pytestmark = [pytest.mark.e2e]


@pytest.mark.skip(reason="Requiere servidor vivo (live_server) y Playwright configurado")
class TestAdminNavigation:
    async def test_admin_login_page(self, page, live_server):
        await page.goto(f"{live_server.url}/admin/login/")
        assert "Iniciar" in await page.title() or "admin" in await page.content()

    async def test_health_page(self, page, logged_in_page):
        await logged_in_page.goto(f"{logged_in_page.url}/health/")
        content = await logged_in_page.content()
        assert "ok" in content.lower() or "health" in content.lower()
