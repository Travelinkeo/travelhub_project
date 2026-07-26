"""Tests para el admin de APISecret — registro, acciones, display."""

import pytest

pytestmark = [pytest.mark.django_db, pytest.mark.admin]


class MockRequest:
    """MockRequest."""

    def __init__(self, user=None):
        """__init__."""
        self.user = user
        self.META = {"SERVER_NAME": "test", "SERVER_PORT": "80"}
        self.session = {}


class TestAPISecretAdminRegistration:
    """TestAPISecretAdminRegistration."""

    def test_admin_import_exists(self):
        """test_admin_import_exists."""
        from core.admin import api_secret_admin

        assert api_secret_admin is not None

    def test_admin_has_list_display(self):
        """test_admin_has_list_display."""
        from core.admin.api_secret_admin import APISecretAdmin

        assert "service_colored" in APISecretAdmin.list_display
        assert "category_badge" in APISecretAdmin.list_display
        assert "is_active" in APISecretAdmin.list_display
        assert "value_masked" in APISecretAdmin.list_display

    def test_admin_has_search_fields(self):
        """test_admin_has_search_fields."""
        from core.admin.api_secret_admin import APISecretAdmin

        assert "service" in APISecretAdmin.search_fields
