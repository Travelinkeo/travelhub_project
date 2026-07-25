"""Tests para el admin de APISecret — registro, acciones, display."""

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.admin]


class MockRequest:
    """Mock Request."""
    def __init__(self, user=None):
        self.user = user
        self.META = {"SERVER_NAME": "test", "SERVER_PORT": "80"}
        self.session = {}


class TestAPISecretAdminRegistration:
    """Test Apisecret Admin Registration."""
    def test_admin_import_exists(self):
        """Admin import exists."""
        from core.admin import api_secret_admin

        assert api_secret_admin is not None

    def test_admin_has_list_display(self):
        """Admin has list display."""
        from core.admin.api_secret_admin import APISecretAdmin

        assert "service_colored" in APISecretAdmin.list_display
        assert "category_badge" in APISecretAdmin.list_display
        assert "is_active" in APISecretAdmin.list_display
        assert "value_masked" in APISecretAdmin.list_display

    def test_admin_has_search_fields(self):
        """Admin has search fields."""
        from core.admin.api_secret_admin import APISecretAdmin

        assert "service" in APISecretAdmin.search_fields
