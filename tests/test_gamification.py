from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.gamification.models import Logro, LogroProgreso, Nivel, PuntuacionUsuario
from apps.gamification.services import REGISTRY, evaluar_logros
from core.models.agencia import Agencia


class NivelModelTest(TestCase):
    """NivelModelTest."""

    def setUp(self):
        """setUp."""
        self.n1 = Nivel.objects.create(nombre="Bronce", puntos_minimos=0)
        self.n2 = Nivel.objects.create(nombre="Plata", puntos_minimos=100)
        self.n3 = Nivel.objects.create(nombre="Oro", puntos_minimos=500)

    def test_ordering_by_puntos_minimos(self):
        """test_ordering_by_puntos_minimos."""
        niveles = list(Nivel.objects.all())
        self.assertEqual(niveles[0].puntos_minimos, 0)
        self.assertEqual(niveles[2].puntos_minimos, 500)

    def test_str(self):
        """test_str."""
        self.assertEqual(str(self.n1), "Bronce")

    def test_default_icono_and_color(self):
        """test_default_icono_and_color."""
        self.assertEqual(self.n1.icono, "stars")
        self.assertEqual(self.n1.color, "#6B7280")


class LogroModelTest(TestCase):
    """LogroModelTest."""

    def setUp(self):
        """setUp."""
        self.logro = Logro.objects.create(
            codigo="test_logro", nombre="Test Logro", puntos=25, categoria="especial"
        )

    def test_str(self):
        """test_str."""
        self.assertEqual(str(self.logro), "Test Logro")

    def test_codigo_unique(self):
        """test_codigo_unique."""
        with self.assertRaises(IntegrityError):
            Logro.objects.create(codigo="test_logro", nombre="Duplicado")

    def test_defaults(self):
        """test_defaults."""
        self.assertTrue(self.logro.activo)
        self.assertEqual(self.logro.icono, "emoji_events")

    def test_categorias(self):
        """test_categorias."""
        for cat_code, _ in Logro.CATEGORIAS:
            logro_obj = Logro.objects.create(
                codigo=f"cat_{cat_code}", nombre=cat_code, categoria=cat_code
            )
            self.assertEqual(logro_obj.categoria, cat_code)


class LogroProgresoModelTest(TestCase):
    """LogroProgresoModelTest."""

    def setUp(self):
        """setUp."""
        self.user = get_user_model().objects.create_user(username="progreso_user")
        self.agencia = Agencia.objects.create(nombre="Test Agency")
        self.logro = Logro.objects.create(codigo="prog_test", nombre="Progreso Test")
        self.progreso = LogroProgreso.objects.create(
            usuario=self.user, logro=self.logro, agencia=self.agencia
        )

    def test_defaults(self):
        """test_defaults."""
        self.assertEqual(self.progreso.progreso, 0)
        self.assertFalse(self.progreso.completado)

    def test_completado(self):
        """test_completado."""
        self.progreso.progreso = 100
        self.progreso.completado = True
        self.progreso.save()
        self.assertTrue(self.progreso.completado)

    def test_unique_together(self):
        """test_unique_together."""
        with self.assertRaises(IntegrityError):
            LogroProgreso.objects.create(usuario=self.user, logro=self.logro, agencia=self.agencia)

    def test_str(self):
        """test_str."""
        self.assertIn("progreso_user", str(self.progreso))


class PuntuacionUsuarioModelTest(TestCase):
    """PuntuacionUsuarioModelTest."""

    def setUp(self):
        """setUp."""
        self.user = get_user_model().objects.create_user(username="punt_user")
        self.agencia = Agencia.objects.create(nombre="Punt Agency")
        self.nivel = Nivel.objects.create(nombre="Bronce", puntos_minimos=0)
        self.punt = PuntuacionUsuario.objects.create(
            usuario=self.user, agencia=self.agencia, puntos_total=50, nivel=self.nivel
        )

    def test_defaults(self):
        """test_defaults."""
        self.assertEqual(self.punt.logros_completados, 0)

    def test_str(self):
        """test_str."""
        self.assertIn("punt_user: 50 pts", str(self.punt))

    def test_unique_together(self):
        """test_unique_together."""
        with self.assertRaises(IntegrityError):
            PuntuacionUsuario.objects.create(usuario=self.user, agencia=self.agencia)


class GamificationServicesTest(TestCase):
    """GamificationServicesTest."""

    def setUp(self):
        """setUp."""
        self.user = get_user_model().objects.create_user(username="service_user")
        self.agencia = Agencia.objects.create(nombre="Service Agency")
        Nivel.objects.create(nombre="Bronce", puntos_minimos=0)
        Nivel.objects.create(nombre="Plata", puntos_minimos=100)

    def test_registry_has_evaluators(self):
        """test_registry_has_evaluators."""
        self.assertIn("primera_venta", REGISTRY)
        self.assertIn("primer_boleto", REGISTRY)
        self.assertIn("cinco_ventas", REGISTRY)

    def test_evaluar_sin_logros_activos(self):
        """test_evaluar_sin_logros_activos."""
        cambios = evaluar_logros(self.agencia, self.user, evento="test")
        self.assertEqual(cambios, [])

    def test_evaluar_logro_no_existente(self):
        """test_evaluar_logro_no_existente."""
        Logro.objects.create(codigo="no_existe_evaluador", nombre="Sin Evaluador", activo=True)
        cambios = evaluar_logros(self.agencia, self.user, evento="test")
        self.assertEqual(cambios, [])

    def test_evaluar_logro_con_evaluador(self):
        """test_evaluar_logro_con_evaluador."""
        Logro.objects.create(codigo="primera_venta", nombre="Primera Venta", activo=True, puntos=50)
        cambios = evaluar_logros(self.agencia, self.user, evento="venta_creada")
        self.assertEqual(cambios, [])

    def test_puntuacion_creada_al_evaluar(self):
        """test_puntuacion_creada_al_evaluar."""
        Logro.objects.create(codigo="primera_venta", nombre="PV", activo=True, puntos=50)
        evaluar_logros(self.agencia, self.user, evento="venta_creada")
        punt = PuntuacionUsuario.objects.filter(usuario=self.user, agencia=self.agencia).first()
        self.assertIsNotNone(punt)
        self.assertEqual(punt.puntos_total, 0)

    def test_logro_progreso_creado(self):
        """test_logro_progreso_creado."""
        Logro.objects.create(codigo="primera_venta", nombre="PV", activo=True, puntos=50)
        evaluar_logros(self.agencia, self.user, evento="venta_creada")
        prog = LogroProgreso.objects.filter(usuario=self.user, agencia=self.agencia).first()
        self.assertIsNotNone(prog)


class GamificationViewsTest(TestCase):
    """GamificationViewsTest."""

    def setUp(self):
        """setUp."""
        self.user = get_user_model().objects.create_user(username="gamif_view", password="pass1234")
        self.agencia = Agencia.objects.create(nombre="View Agency")
        Nivel.objects.create(nombre="Bronce", puntos_minimos=0)
        Nivel.objects.create(nombre="Plata", puntos_minimos=100)
        self.client.login(username="gamif_view", password="pass1234")

    def test_dashboard_requires_login(self):
        """test_dashboard_requires_login."""
        self.client.logout()
        response = self.client.get(reverse("gamification:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_renders(self):
        """test_dashboard_renders."""
        response = self.client.get(reverse("gamification:dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_badges_renders(self):
        """test_badges_renders."""
        response = self.client.get(reverse("gamification:badges"))
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_renders(self):
        """test_leaderboard_renders."""
        response = self.client.get(reverse("gamification:leaderboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_shows_score(self):
        """test_dashboard_shows_score."""
        PuntuacionUsuario.objects.create(usuario=self.user, agencia=self.agencia, puntos_total=75)
        response = self.client.get(reverse("gamification:dashboard"))
        self.assertContains(response, "75")

    def test_leaderboard_shows_users(self):
        """test_leaderboard_shows_users."""
        other = get_user_model().objects.create_user(username="other_user")
        PuntuacionUsuario.objects.create(usuario=self.user, agencia=self.agencia, puntos_total=100)
        PuntuacionUsuario.objects.create(usuario=other, agencia=self.agencia, puntos_total=50)
        response = self.client.get(reverse("gamification:leaderboard"))
        self.assertContains(response, "gamif_view")
        self.assertContains(response, "other_user")


class GamificationSignalsTest(TestCase):
    """GamificationSignalsTest."""

    def setUp(self):
        """setUp."""
        self.user = get_user_model().objects.create_user(username="signal_user")
        self.agencia = Agencia.objects.create(nombre="Signal Agency")
        Nivel.objects.create(nombre="Bronce", puntos_minimos=0)
        Logro.objects.create(codigo="primera_venta", nombre="PV", activo=True, puntos=50)
        Logro.objects.create(codigo="primer_boleto", nombre="PB", activo=True, puntos=30)

    def test_signal_venta_creada(self):
        """test_signal_venta_creada."""
        from apps.bookings.models import Venta
        from apps.common.models import Moneda
        from apps.crm.models import Cliente

        moneda = Moneda.objects.create(codigo_iso="USD", nombre="Dólar", simbolo="$")
        cliente = Cliente.objects.create(nombres="Test", apellidos="Client", agencia=self.agencia)
        Venta.objects.create(
            cliente=cliente, moneda=moneda, agencia=self.agencia, creado_por=self.user
        )
        prog = LogroProgreso.objects.filter(usuario=self.user, agencia=self.agencia).first()
        self.assertIsNotNone(prog)
        self.assertEqual(prog.logro.codigo, "primera_venta")
