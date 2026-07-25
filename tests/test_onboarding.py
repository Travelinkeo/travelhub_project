"""
Tests para el Onboarding Wizard de TravelHub.

Estos tests verifican:
1. El modelo UserProgress funciona correctamente
2. Las vistas del wizard responden correctamente
3. El middleware redirige usuarios nuevos
"""

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.common.models import UserProgress


class UserProgressModelTest(TestCase):
    """Tests para el modelo UserProgress."""

    def setUp(self):
        """SetUp."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_create_progress(self):
        """Test: Crear progreso de onboarding."""
        progress = UserProgress.objects.create(user=self.user)

        self.assertEqual(progress.user, self.user)
        self.assertEqual(progress.current_step, UserProgress.STEP_WELCOME)
        self.assertEqual(progress.completed_steps, [])
        self.assertFalse(progress.onboarding_completed)

    def test_mark_step_completed(self):
        """Test: Marcar un paso como completado."""
        progress = UserProgress.objects.create(user=self.user)

        progress.mark_step_completed(UserProgress.STEP_WELCOME)

        self.assertIn(UserProgress.STEP_WELCOME, progress.completed_steps)
        self.assertEqual(progress.current_step, UserProgress.STEP_AGENCY)
        self.assertFalse(progress.onboarding_completed)

    def test_complete_all_steps(self):
        """Test: Completar todos los pasos."""
        progress = UserProgress.objects.create(user=self.user)

        for step in UserProgress.ALL_STEPS:
            progress.mark_step_completed(step)

        self.assertTrue(progress.onboarding_completed)
        self.assertEqual(progress.get_next_step(), None)
        self.assertEqual(progress.get_progress_percentage(), 100)

    def test_invalid_step(self):
        """Test: Intentar marcar un paso inválido."""
        progress = UserProgress.objects.create(user=self.user)

        with self.assertRaises(ValueError):
            progress.mark_step_completed("invalid_step")

    def test_progress_percentage(self):
        """Test: Calcular porcentaje de progreso."""
        progress = UserProgress.objects.create(user=self.user)

        self.assertEqual(progress.get_progress_percentage(), 0)

        progress.mark_step_completed(UserProgress.STEP_WELCOME)
        self.assertEqual(progress.get_progress_percentage(), 20)

        progress.mark_step_completed(UserProgress.STEP_AGENCY)
        self.assertEqual(progress.get_progress_percentage(), 40)

    def test_reset(self):
        """Test: Reiniciar progreso."""
        progress = UserProgress.objects.create(user=self.user)
        progress.mark_step_completed(UserProgress.STEP_WELCOME)
        progress.mark_step_completed(UserProgress.STEP_AGENCY)

        progress.reset()

        self.assertEqual(progress.completed_steps, [])
        self.assertEqual(progress.current_step, UserProgress.STEP_WELCOME)
        self.assertFalse(progress.onboarding_completed)

    def test_str_representation(self):
        """Test: Representación en string."""
        progress = UserProgress.objects.create(user=self.user)

        self.assertIn("testuser", str(progress))
        self.assertIn("0%", str(progress))

        progress.mark_step_completed(UserProgress.STEP_WELCOME)
        progress.mark_step_completed(UserProgress.STEP_AGENCY)
        progress.mark_step_completed(UserProgress.STEP_FIRST_TICKET)
        progress.mark_step_completed(UserProgress.STEP_INVITE_TEAM)
        progress.mark_step_completed(UserProgress.STEP_COMPLETE)

        self.assertIn("Completado", str(progress))


class OnboardingViewsTest(TestCase):
    """Tests para las vistas del wizard."""

    def setUp(self):
        """Setup."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_welcome_view_GET(self):
        """Test: Vista de bienvenida responde OK."""
        response = self.client.get(reverse("onboarding_welcome"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bienvenido")

    def test_welcome_view_POST(self):
        """Test: POST en bienvenida avanza al siguiente paso."""
        response = self.client.post(reverse("onboarding_welcome"))

        self.assertEqual(response.status_code, 302)  # Redirect

        # Verificar que se creó el progreso
        progress = UserProgress.objects.get(user=self.user)
        self.assertIn(UserProgress.STEP_WELCOME, progress.completed_steps)
        self.assertEqual(progress.current_step, UserProgress.STEP_AGENCY)

    def test_agency_view_requires_welcome(self):
        """Test: No se puede saltar al paso 2 sin completar el 1."""
        response = self.client.get(reverse("onboarding_agency"))

        # Debe redirigir al paso 1
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("onboarding_welcome"), response.url)

    def test_agency_view_after_welcome(self):
        """Test: Paso 2 funciona después de completar paso 1."""
        # Completar paso 1
        self.client.post(reverse("onboarding_welcome"))

        response = self.client.get(reverse("onboarding_agency"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configura tu Agencia")

    def test_skip_onboarding(self):
        """Test: Saltar onboarding completa todos los pasos."""
        response = self.client.post(reverse("onboarding_skip"))

        self.assertEqual(response.status_code, 302)

        # Verificar que se completó
        progress = UserProgress.objects.get(user=self.user)
        self.assertTrue(progress.onboarding_completed)

    def test_progress_api(self):
        """Test: API de progreso retorna JSON válido."""
        response = self.client.get(reverse("onboarding_progress"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = response.json()
        self.assertIn("completed", data)
        self.assertIn("current_step", data)
        self.assertIn("percentage", data)


class OnboardingMiddlewareTest(TestCase):
    """Tests para el middleware de redirección."""

    def setUp(self):
        """Setup."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_redirect_to_wizard(self):
        """Test: Usuario nuevo es redirigido al wizard."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get("/dashboard/")

        # Debe redirigir al wizard
        self.assertEqual(response.status_code, 302)
        self.assertIn("/onboarding/wizard/", response.url)

    def test_no_redirect_for_completed(self):
        """Test: Usuario completado NO es redirigido."""
        self.client.login(username="testuser", password="testpass123")

        # Completar onboarding
        UserProgress.objects.create(
            user=self.user,
            completed_steps=UserProgress.ALL_STEPS.copy(),
            current_step=UserProgress.STEP_COMPLETE,
        )

        response = self.client.get("/dashboard/")

        # No debe redirigir al wizard
        # (puede retornar 200 o redirigir a otra cosa, pero no a /onboarding/)
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)

    def test_skip_api_paths(self):
        """Test: Las rutas de API no son interceptadas."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get("/api/ventas/")

        # No debe redirigir al wizard (aunque pueda fallar por otros motivos)
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)

    def test_skip_htmx(self):
        """Test: Requests HTMX no son interceptados."""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(
            "/dashboard/",
            HTTP_HX_REQUEST="true",
        )

        # No debe redirigir al wizard
        if response.status_code == 302:
            self.assertNotIn("/onboarding/", response.url)
