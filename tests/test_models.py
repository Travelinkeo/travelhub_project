"""Tests para Models."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from core.models.agencia import Agencia, AgenciaBranding, AgenciaConfiguracion, UsuarioAgencia

User = get_user_model()


class AgenciaModelTest(TestCase):
    """Agencia Model Test."""
    def test_create_agencia(self):
        """Create agencia."""
        agencia = Agencia.objects.create(
            nombre="Test Agency",
            email_principal="test@agency.com",
        )
        self.assertEqual(agencia.nombre, "Test Agency")
        self.assertTrue(agencia.activa)

    def test_agencia_slug_auto_generated(self):
        """Agencia slug auto generated."""
        agencia = Agencia.objects.create(
            nombre="Mi Agencia de Viajes", email_principal="test2@agency.com"
        )
        self.assertIsNotNone(agencia.subdominio_slug)

    def test_save_crea_configuracion_y_branding(self):
        """Save crea configuracion y branding."""
        agencia = Agencia.objects.create(nombre="SaveTest", email_principal="save@test.com")
        self.assertIsNotNone(agencia.configuracion)
        self.assertIsNotNone(agencia.branding)
        self.assertIsInstance(agencia.configuracion, AgenciaConfiguracion)
        self.assertIsInstance(agencia.branding, AgenciaBranding)

    def test_slug_is_unique(self):
        """Slug is unique."""
        a1 = Agencia.objects.create(nombre="Slug Test", email_principal="st1@test.com")
        a2 = Agencia.objects.create(nombre="Otro Test", email_principal="st2@test.com")
        self.assertIsNotNone(a1.configuracion.subdominio_slug)
        self.assertIsNotNone(a2.configuracion.subdominio_slug)
        self.assertNotEqual(
            a1.configuracion.subdominio_slug,
            a2.configuracion.subdominio_slug,
        )

    def test_usuario_agencia_creation(self):
        """Usuario agencia creation."""
        user = User.objects.create_user(
            username="testuser", email="test@test.com", password="test123"
        )
        agencia = Agencia.objects.create(nombre="Test", email_principal="test3@agency.com")
        ua = UsuarioAgencia.objects.create(
            usuario=user,
            agencia=agencia,
            rol="admin",
        )
        self.assertEqual(ua.rol, "admin")
        self.assertTrue(ua.activo)

    def test_puede_crear_venta_delega_a_quota(self):
        """Puede crear venta delega a quota."""
        agencia = Agencia.objects.create(nombre="QuotaTest", email_principal="quota@test.com")
        with patch(
            "apps.common.services.saas_quota_service.SaaSQuotaService.check_quota",
            return_value=True,
        ) as mock_check:
            result = agencia.puede_crear_venta()
            self.assertTrue(result)
            mock_check.assert_called_once_with(agencia, "sales_per_month")

    def test_puede_agregar_usuario_delega_a_quota(self):
        """Puede agregar usuario delega a quota."""
        agencia = Agencia.objects.create(nombre="UserQuota", email_principal="uq@test.com")
        with patch(
            "apps.common.services.saas_quota_service.SaaSQuotaService.check_quota",
            return_value=False,
        ) as mock_check:
            result = agencia.puede_agregar_usuario()
            self.assertFalse(result)
            mock_check.assert_called_once_with(agencia, "users")

    @override_settings(
        SAAS_PLAN_LIMITS={
            "PRO": {"users": 15, "sales_per_month": 500},
            "FREE": {"users": 3, "sales_per_month": 20},
        }
    )
    def test_actualizar_limites_por_plan_pro(self):
        """Actualizar limites por plan pro."""
        agencia = Agencia.objects.create(nombre="PlanTest", email_principal="plan@test.com")
        agencia.configuracion.plan = "PRO"
        agencia.configuracion.save()
        agencia.actualizar_limites_por_plan()
        agencia.configuracion.refresh_from_db()
        self.assertEqual(agencia.configuracion.limite_usuarios, 15)
        self.assertEqual(agencia.configuracion.limite_ventas_mes, 500)

    @override_settings(
        SAAS_PLAN_LIMITS={
            "PRO": {"users": 15, "sales_per_month": 500},
            "FREE": {"users": 3, "sales_per_month": 20},
        }
    )
    def test_actualizar_limites_por_plan_free_default(self):
        """Actualizar limites por plan free default."""
        agencia = Agencia.objects.create(nombre="FreeTest", email_principal="free@test.com")
        agencia.actualizar_limites_por_plan()
        agencia.configuracion.refresh_from_db()
        self.assertEqual(agencia.configuracion.limite_usuarios, 3)
        self.assertEqual(agencia.configuracion.limite_ventas_mes, 20)

    def test_es_contribuyente_especial_false_por_defecto(self):
        """Es contribuyente especial false por defecto."""
        agencia = Agencia.objects.create(nombre="ContribTest", email_principal="contrib@test.com")
        self.assertFalse(agencia.es_contribuyente_especial)

    def test_es_contribuyente_especial_true(self):
        """Es contribuyente especial true."""
        agencia = Agencia.objects.create(nombre="Esp", email_principal="esp@test.com")
        agencia.configuracion.es_sujeto_pasivo_especial = True
        agencia.configuracion.save()
        self.assertTrue(agencia.es_contribuyente_especial)

    def test_configuracion_correo_retorna_dict(self):
        """Configuracion correo retorna dict."""
        agencia = Agencia.objects.create(nombre="EmailConf", email_principal="email@test.com")
        cfg = agencia.configuracion_correo
        self.assertIn("EMAIL_HOST", cfg)
        self.assertIn("EMAIL_PORT", cfg)
        self.assertEqual(cfg["EMAIL_PORT"], 587)

    def test_configuracion_correo_sin_config(self):
        """Configuracion correo sin config."""
        agencia = Agencia()
        self.assertEqual(agencia.configuracion_correo, {})

    def test_properties_con_defaults(self):
        """Properties con defaults."""
        agencia = Agencia.objects.create(nombre="Defaults", email_principal="def@test.com")
        self.assertEqual(agencia.moneda_principal, "USD")
        self.assertEqual(agencia.color_primario, "#1976d2")
        self.assertEqual(agencia.ui_theme, "obsidian")
        self.assertEqual(agencia.plantilla_boletos, "m1")
        self.assertEqual(agencia.plantilla_vouchers, "m1")
        self.assertEqual(agencia.plantilla_facturas, "m1")

    def test_plan_property(self):
        """Plan property."""
        agencia = Agencia.objects.create(nombre="PlanProp", email_principal="prop@test.com")
        self.assertEqual(agencia.plan, "FREE")
        agencia.configuracion.plan = "PRO"
        agencia.configuracion.save()
        self.assertEqual(agencia.plan, "PRO")


class UserModelTest(TestCase):
    """User Model Test."""
    def test_create_user(self):
        """Create user."""
        user = User.objects.create_user(
            username="newuser", email="new@test.com", password="pass123"
        )
        self.assertTrue(user.is_active)
        self.assertEqual(user.email, "new@test.com")

    def test_get_or_create_user(self):
        """Get or create user."""
        user, created = User.objects.get_or_create(
            email="magic@test.com", defaults={"username": "magic@test.com", "is_active": True}
        )
        self.assertTrue(created)
        self.assertEqual(user.email, "magic@test.com")

        user2, created2 = User.objects.get_or_create(
            email="magic@test.com", defaults={"username": "magic@test.com", "is_active": True}
        )
        self.assertFalse(created2)
        self.assertEqual(user.id, user2.id)
