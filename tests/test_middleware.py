from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models.agencia import Agencia


class SecurityHeadersMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_x_content_type_options(self):
        response = self.client.get("/login/")
        self.assertIn("X-Content-Type-Options", response)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_x_frame_options(self):
        response = self.client.get("/login/")
        self.assertIn("X-Frame-Options", response)

    def test_referrer_policy(self):
        response = self.client.get("/login/")
        self.assertIn("Referrer-Policy", response)

    def test_content_security_policy(self):
        response = self.client.get("/login/")
        self.assertIn("Content-Security-Policy", response)

    def test_csp_contains_nonce(self):
        response = self.client.get("/login/")
        csp = response["Content-Security-Policy"]
        self.assertIn("nonce-", csp)


class OnboardingRedirectMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="onboard_user", password="pass1234"
        )

    def test_api_paths_not_intercepted(self):
        self.client.login(username="onboard_user", password="pass1234")
        response = self.client.get("/api/ventas/")
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)

    def test_htmx_requests_not_intercepted(self):
        self.client.login(username="onboard_user", password="pass1234")
        response = self.client.get("/dashboard/", HTTP_HX_REQUEST="true")
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)

    def test_static_paths_not_intercepted(self):
        self.client.login(username="onboard_user", password="pass1234")
        response = self.client.get("/static/css/style.css")
        self.assertNotEqual(response.status_code, 302)

    def test_login_page_not_intercepted(self):
        self.client.login(username="onboard_user", password="pass1234")
        response = self.client.get(reverse("core:login"))
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)


class MultiTenantMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username="tenant_user", password="pass1234"
        )
        self.agencia = Agencia.objects.create(
            nombre="Tenant Agency",
            subdominio_slug="tenant-test",
        )

    def test_request_without_agency_does_not_crash(self):
        self.client.login(username="tenant_user", password="pass1234")
        response = self.client.get("/login/")
        self.assertIn(response.status_code, [200, 302])
