"""Tests para el admin de APISecret — registro, acciones, display."""

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model

pytestmark = [pytest.mark.django_db, pytest.mark.admin]


class MockRequest:
    def __init__(self, user=None):
        self.user = user
        self.META = {"SERVER_NAME": "test", "SERVER_PORT": "80"}
        self.session = {}


class TestAPISecretAdminRegistration:
    def test_admin_import_exists(self):
        from core.admin import api_secret_admin

        assert api_secret_admin is not None

    def test_admin_has_list_display(self):
        from core.admin import APISecretAdmin

        assert "service" in APISecretAdmin.list_display
        assert "category" in APISecretAdmin.list_display
        assert "is_active" in APISecretAdmin.list_display

    def test_admin_has_search_fields(self):
        from core.admin import APISecretAdmin

        assert "service" in APISecretAdmin.search_fields


class TestFeatureFlagAdmin:
    def test_list_display(self):
        from core.admin import FeatureFlagAdmin

        assert "nombre" in FeatureFlagAdmin.list_display


class TestCronApiKeyAdmin:
    def test_list_display(self):
        from core.admin import CronApiKeyAdmin

        assert "nombre" in CronApiKeyAdmin.list_display
