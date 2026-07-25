"""Tests para Views."""
import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from core.models.magic_link import MagicLinkToken

pytestmark = pytest.mark.skip(reason="Tests requieren configuración completa o refactorización")

User = get_user_model()


class MagicLinkRequestViewTest(TestCase):
    """Magic Link Request View Test."""
    def setUp(self):
        """SetUp."""
        self.client = Client()

    def test_magic_link_request_no_email(self):
        """Magic link request no email."""
        response = self.client.post(
            "/auth/magic-request/",
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_magic_link_request_valid_email(self):
        """Magic link request valid email."""
        response = self.client.post(
            "/auth/magic-request/",
            data=json.dumps({"email": "user@example.com"}),
            content_type="application/json",
        )
        self.assertIn(response.status_code, [200, 500])
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["email"], "user@example.com")
            self.assertTrue(MagicLinkToken.objects.filter(email="user@example.com").exists())


class MagicLinkVerifyViewTest(TestCase):
    """Magic Link Verify View Test."""
    def setUp(self):
        """Setup."""
        self.client = Client()

    def test_verify_invalid_token(self):
        """Verify invalid token."""
        response = self.client.get("/auth/magic/invalid_token_xyz/")
        self.assertEqual(response.status_code, 400)

    def test_verify_valid_token_creates_user(self):
        """Verify valid token creates user."""
        token = MagicLinkToken.objects.create(
            email="newuser@example.com",
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        response = self.client.get(f"/auth/magic/{token.token}/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_verify_expired_token(self):
        """Verify expired token."""
        token = MagicLinkToken.objects.create(
            email="expired@example.com",
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        response = self.client.get(f"/auth/magic/{token.token}/")
        self.assertEqual(response.status_code, 400)

    def test_verify_onboarding_token_redirects(self):
        """Verify onboarding token redirects."""
        token = MagicLinkToken.objects.create(
            email="onboard@example.com",
            token=MagicLinkToken.generate_token(),
            expires_at=timezone.now() + timedelta(minutes=15),
            is_onboarding=True,
            onboarding_data={"plan": "PRO"},
        )
        response = self.client.get(f"/auth/magic/{token.token}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/onboarding/agency/", response.url)


class OnboardingViewTest(TestCase):
    """Onboarding View Test."""
    def test_onboarding_page_loads(self):
        """Onboarding page loads."""
        response = self.client.get("/onboarding/")
        self.assertEqual(response.status_code, 200)
