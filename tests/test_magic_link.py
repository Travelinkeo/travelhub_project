from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from core.models.magic_link import MagicLinkToken

User = get_user_model()


class MagicLinkTokenModelTest(TestCase):
    """MagicLinkTokenModelTest."""

    def setUp(self):
        """setUp."""
        self.email = "test@example.com"

    def test_create_token(self):
        """test_create_token."""
        token = MagicLinkToken.objects.create(
            email=self.email,
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        self.assertIsNotNone(token.id)
        self.assertEqual(token.email, self.email)
        self.assertTrue(token.is_valid)
        self.assertIsNone(token.used_at)

    def test_expired_token_is_invalid(self):
        """test_expired_token_is_invalid."""
        token = MagicLinkToken.objects.create(
            email=self.email,
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertFalse(token.is_valid)

    def test_used_token_is_invalid(self):
        """test_used_token_is_invalid."""
        token = MagicLinkToken.objects.create(
            email=self.email,
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        token.mark_used()
        self.assertFalse(token.is_valid)
        self.assertIsNotNone(token.used_at)

    def test_generate_token_is_unique(self):
        """test_generate_token_is_unique."""
        t1 = MagicLinkToken.generate_token()
        t2 = MagicLinkToken.generate_token()
        self.assertNotEqual(t1, t2)

    def test_invalidate_previous_tokens(self):
        """test_invalidate_previous_tokens."""
        t1 = MagicLinkToken.objects.create(
            email=self.email,
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        MagicLinkToken.objects.filter(email=self.email, used_at__isnull=True).update(
            used_at=timezone.now()
        )

        t1.refresh_from_db()
        self.assertIsNotNone(t1.used_at)

    def test_onboarding_data_stored(self):
        """test_onboarding_data_stored."""
        token = MagicLinkToken.objects.create(
            email=self.email,
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
            is_onboarding=True,
            onboarding_data={"plan": "PRO", "agency_name": "Test Agency"},
        )
        self.assertTrue(token.is_onboarding)
        self.assertEqual(token.onboarding_data["plan"], "PRO")


class MagicLinkServiceTest(TestCase):
    """MagicLinkServiceTest."""

    def test_verify_valid_token(self):
        """test_verify_valid_token."""
        from apps.common.services.magic_link_service import verify_magic_link

        token = MagicLinkToken.objects.create(
            email="verify@example.com",
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        result, status = verify_magic_link(token.token)
        self.assertEqual(status, "valid")
        self.assertEqual(result.email, "verify@example.com")

    def test_verify_expired_token(self):
        """test_verify_expired_token."""
        from apps.common.services.magic_link_service import verify_magic_link

        token = MagicLinkToken.objects.create(
            email="expired@example.com",
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        result, status = verify_magic_link(token.token)
        self.assertEqual(status, "expired")

    def test_verify_invalid_token(self):
        """test_verify_invalid_token."""
        from apps.common.services.magic_link_service import verify_magic_link

        result, status = verify_magic_link("nonexistent_token_12345")
        self.assertEqual(status, "invalid")
        self.assertIsNone(result)

    def test_verify_marks_token_as_used(self):
        """test_verify_marks_token_as_used."""
        from apps.common.services.magic_link_service import verify_magic_link

        token = MagicLinkToken.objects.create(
            email="used@example.com",
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        verify_magic_link(token.token)
        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)
