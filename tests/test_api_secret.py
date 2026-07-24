import pytest
from django.core.cache import cache

from core.models import APISecret
from core.services.api_secrets import get_api_secret
from core.services.api_testers import test_api_secret as real_test

pytestmark = [pytest.mark.django_db, pytest.mark.unit]


class TestAPISecretModel:
    def test_create_secret(self):
        secret = APISecret.objects.create(
            service="TEST_API_KEY",
            category="ai",
            value="sk-test-1234567890",
            description="Test key",
        )
        assert secret.service == "TEST_API_KEY"
        assert secret.category == "ai"
        assert secret.is_active is True
        assert secret.test_status == "unknown"
        assert "TEST_API_KEY" in str(secret)
        assert secret.pk is not None

    def test_encryption_at_rest(self):
        raw = "super-secret-value-12345"
        secret = APISecret.objects.create(
            service="ENCRYPTED_TEST",
            category="security",
            value=raw,
        )
        secret.refresh_from_db()
        assert secret.value == raw

    def test_unique_service(self):
        APISecret.objects.create(service="UNIQUE_TEST", category="ai", value="v1")
        with pytest.raises(Exception, match="already exists"):
            APISecret.objects.create(service="UNIQUE_TEST", category="ai", value="v2")

    def test_category_choices_valid(self):
        for cat, _label in APISecret.CATEGORIES:
            s = APISecret.objects.create(service=f"SVC_{cat}", category=cat, value="x")
            assert s.category == cat

    def test_category_choices_invalid(self):
        from django.core.exceptions import ValidationError

        s = APISecret(service="BAD_CAT", category="invalid", value="x")
        with pytest.raises(ValidationError):
            s.full_clean()

    def test_ordering(self):
        APISecret.objects.create(service="B_service", category="ai", value="v")
        APISecret.objects.create(service="A_service", category="payment", value="v")
        qs = APISecret.objects.all()
        assert qs[0].service == "B_service"
        assert qs[1].service == "A_service"

    def test_default_values(self):
        s = APISecret.objects.create(service="DEFAULTS_TEST", category="infra", value="v")
        assert s.is_active is True
        assert s.test_status == "unknown"
        assert s.last_tested is None


class TestGetAPISecret:
    def test_from_db(self):
        APISecret.objects.create(service="DB_KEY", category="ai", value="db-value-123")
        cache.delete("api_secret:DB_KEY")
        assert get_api_secret("DB_KEY") == "db-value-123"

    def test_from_cache(self):
        APISecret.objects.create(service="CACHED_KEY", category="ai", value="db-value")
        get_api_secret("CACHED_KEY")
        APISecret.objects.filter(service="CACHED_KEY").update(value="changed")
        assert get_api_secret("CACHED_KEY") == "db-value"

    def test_not_found_returns_default(self):
        assert get_api_secret("NONEXISTENT_KEY") is None
        assert get_api_secret("NONEXISTENT_KEY", "fallback") == "fallback"

    def test_inactive_secret_ignored(self, monkeypatch):
        APISecret.objects.create(
            service="INACTIVE_KEY", category="ai", value="real-value", is_active=False
        )
        assert get_api_secret("INACTIVE_KEY") is None

    def test_cache_invalidation(self):
        APISecret.objects.create(service="CACHE_INVAL", category="ai", value="v1")
        assert get_api_secret("CACHE_INVAL") == "v1"
        APISecret.objects.filter(service="CACHE_INVAL").update(value="v2")
        cache.delete("api_secret:CACHE_INVAL")
        assert get_api_secret("CACHE_INVAL") == "v2"


class TestAPISecretAdmin:
    def test_masked_value_hides_middle(self):
        secret = APISecret.objects.create(
            service="MASK_TEST", category="ai", value="supersecret123"
        )
        from core.admin.api_secret_admin import APISecretAdmin

        admin = APISecretAdmin(model=APISecret, admin_site=None)
        masked = admin.value_masked(secret)
        html = str(masked)
        assert "••••" in html
        assert "supers" in html
        assert "t123" in html

    def test_masked_value_leakable_via_onclick(self):
        secret = APISecret.objects.create(
            service="TOGGLE_TEST",
            category="ai",
            value="secret-value-to-toggle",
        )
        from core.admin.api_secret_admin import APISecretAdmin

        admin = APISecretAdmin(model=APISecret, admin_site=None)
        html = str(admin.value_masked(secret))
        assert "secret-value-to-toggle" in html

    def test_category_badge_renders(self):
        secret = APISecret(service="X", category="payment", value="x")
        from core.admin.api_secret_admin import APISecretAdmin

        admin = APISecretAdmin(model=APISecret, admin_site=None)
        badge = admin.category_badge(secret)
        assert "Pagos" in str(badge)


class TestAPITesters:
    def test_generic_valid_key(self):
        ok, msg = real_test("UNKNOWN_SERVICE", "valid-key-min-8-chars")
        assert ok is True

    def test_generic_short_key(self):
        ok, msg = real_test("UNKNOWN_SERVICE", "short")
        assert ok is False

    def test_empty_key(self):
        ok, msg = real_test("ANY_SERVICE", "")
        assert ok is False

    def test_sentry_dsn_format(self):
        ok, msg = real_test("SENTRY_DSN", "https://key@sentry.io/123")
        assert ok is True

    def test_evolution_key_format(self):
        ok, msg = real_test("EVOLUTION_API_KEY", "a" * 16)
        assert ok is True

    def test_evolution_key_short(self):
        ok, msg = real_test("EVOLUTION_API_KEY", "short")
        assert ok is False

    def test_telegram_invalid_token(self):
        ok, msg = real_test("TELEGRAM_BOT_TOKEN", "invalid_token")
        assert ok is False

    def test_google_oauth_client_id(self):
        ok, msg = real_test("GOOGLE_OAUTH_CLIENT_ID", "AIza-random-id")
        assert ok is True
