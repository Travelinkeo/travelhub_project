"""Tests para Middleware."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models.agencia import Agencia


class SecurityHeadersMiddlewareTest(TestCase):
    """Security Headers Middleware Test."""
    def setUp(self):
        """SetUp."""
        self.client = Client()

    def test_x_content_type_options(self):
        """X content type options."""
        response = self.client.get("/login/")
        self.assertIn("X-Content-Type-Options", response)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_x_frame_options(self):
        """X frame options."""
        response = self.client.get("/login/")
        self.assertIn("X-Frame-Options", response)

    def test_referrer_policy(self):
        """Referrer policy."""
        response = self.client.get("/login/")
        self.assertIn("Referrer-Policy", response)

    def test_content_security_policy(self):
        """Content security policy."""
        response = self.client.get("/login/")
        self.assertIn("Content-Security-Policy", response)

    def test_csp_contains_nonce(self):
        """Csp contains nonce."""
        response = self.client.get("/login/")
        csp = response["Content-Security-Policy"]
        self.assertIn("nonce-", csp)


class OnboardingRedirectMiddlewareTest(TestCase):
    """Onboarding Redirect Middleware Test."""
    def setUp(self):
        """Setup."""
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="onboard_user", password="pass1234"
        )

    def test_api_paths_not_intercepted(self):
        """Api paths not intercepted."""
        self.client.login(username="onboard_user", password="pass1234")
        response = self.client.get("/api/ventas/")
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)

    def test_htmx_requests_not_intercepted(self):
        """Htmx requests not intercepted."""
        self.client.login(username="onboard_user", password="pass1234")
        response = self.client.get("/dashboard/", HTTP_HX_REQUEST="true")
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)

    def test_static_paths_not_intercepted(self):
        """Static paths not intercepted."""
        self.client.login(username="onboard_user", password="pass1234")
        response = self.client.get("/static/css/style.css")
        self.assertNotEqual(response.status_code, 302)

    def test_login_page_not_intercepted(self):
        """Login page not intercepted."""
        self.client.login(username="onboard_user", password="pass1234")
        response = self.client.get(reverse("core:login"))
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)


class MultiTenantMiddlewareTest(TestCase):
    """Multi Tenant Middleware Test."""
    def setUp(self):
        """Setup."""
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="tenant_user", password="pass1234"
        )
        self.agencia = Agencia.objects.create(
            nombre="Tenant Agency",
            subdominio_slug="tenant-test",
        )

    def test_request_without_agency_does_not_crash(self):
        """Request without agency does not crash."""
        self.client.login(username="tenant_user", password="pass1234")
        response = self.client.get("/login/")
        self.assertIn(response.status_code, [200, 302])
