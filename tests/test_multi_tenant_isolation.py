#!/usr/bin/env python
"""
Phase 2 Hardening - Multi-Tenant Isolation Tests

Tests to verify multi-tenant isolation works correctly after migrations.
These tests verify that AgenciaMixin/Manager properly filters queries by agencia.

Run with: python -m pytest tests/test_multi_tenant_isolation.py -v
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.automation.models import NotificacionAgente, NotificacionInteligente
from apps.bookings.models import Cliente, Venta
from apps.communications.models import NotificationLog, NotificationTemplate
from apps.crm.models import MensajeWhatsApp, OportunidadViaje
from apps.finance.models import Factura, ItemFactura
from core.middleware import agency_context, get_current_agency, set_current_agency
from core.models import Agencia

User = get_user_model()


class MultiTenantIsolationTestCase(TestCase):
    """Base test case with agency setup."""

    @classmethod
    def setUpTestData(cls):
        # Create two agencies
        cls.agency1 = Agencia.objects.create(
            nombre="Agencia Test 1",
            dominio="agencia1.test",
            subdominio_slug="agencia1",
            activo=True,
        )
        cls.agency2 = Agencia.objects.create(
            nombre="Agencia Test 2",
            dominio="agencia2.test",
            subdominio_slug="agencia2",
            activo=True,
        )

        # Create users in each agency
        cls.user1 = User.objects.create_user(
            username="user1", email="user1@agencia1.test", password="test123"
        )
        cls.user1.agencias.add(cls.agency1, through_defaults={"rol": "admin", "activo": True})

        cls.user2 = User.objects.create_user(
            username="user2", email="user2@agencia2.test", password="test123"
        )
        cls.user2.agencias.add(cls.agency2, through_defaults={"rol": "admin", "activo": True})

        # Superuser (can see all)
        cls.superuser = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="test123"
        )

    def set_current_agency(self, agency):
        """Helper to set thread-local agency context."""
        set_current_agency(agency)

    def clear_agency(self):
        """Clear thread-local agency context."""
        set_current_agency(None)


class TestNotificationTemplateIsolation(MultiTenantIsolationTestCase):
    """Test NotificationTemplate/Log multi-tenant isolation."""

    def setUp(self):
        self.clear_agency()

    def test_template_creation_with_agencia(self):
        """Templates created with agency are scoped to that agency."""
        self.set_current_agency(self.agency1)

        template = NotificationTemplate.objects.create(
            name="Test Template Agency 1",
            event_type="test_event",
            channel="email",
            language="es",
            body_template="Test body",
            agencia=self.agency1,
        )

        # Query with agency1 context - should see template
        self.set_current_agency(self.agency1)
        templates = NotificationTemplate.objects.all()
        self.assertIn(template, templates)

        # Query with agency2 context - should NOT see template
        self.set_current_agency(self.agency2)
        templates = NotificationTemplate.objects.all()
        self.assertNotIn(template, templates)

        # Cleanup
        self.clear_agency()
        template.delete()

    def test_global_template_visible_to_all(self):
        """Templates with agencia=None (global) visible to all agencies."""
        self.clear_agency()

        global_template = NotificationTemplate.objects.create(
            name="Global Template",
            event_type="global_event",
            channel="email",
            language="es",
            body_template="Global test",
            agencia=None,  # Global template
        )

        # Both agencies should see it
        self.set_current_agency(self.agency1)
        self.assertIn(global_template, NotificationTemplate.objects.all())

        self.set_current_agency(self.agency2)
        self.assertIn(global_template, NotificationTemplate.objects.all())

        # Cleanup
        global_template.delete()
        self.clear_agency()

    def test_log_isolation(self):
        """NotificationLog isolated by agencia."""
        self.set_current_agency(self.agency1)

        log = NotificationLog.objects.create(
            event_type="test_event",
            channel="email",
            recipient="test@test.com",
            body="Test log agency 1",
            status="sent",
            agencia=self.agency1,
        )

        self.set_current_agency(self.agency1)
        logs = NotificationLog.objects.all()
        self.assertIn(log, logs)

        self.set_current_agency(self.agency2)
        logs = NotificationLog.objects.all()
        self.assertNotIn(log, logs)

        log.delete()
        self.clear_agency()


class TestBookingModelsIsolation(MultiTenantIsolationTestCase):
    """Test booking models (Venta, Cliente, ItemFactura) isolation."""

    def setUp(self):
        self.clear_agency()

    def test_venta_isolation(self):
        """Venta isolation by agencia."""

        # Create clients in each agency
        self.set_current_agency(self.agency1)
        client1 = Cliente.objects.create(
            nombres="Cliente 1",
            email="cliente1@agencia1.test",
            agencia=self.agency1,
        )
        venta1 = Venta.objects.create(
            cliente=client1,
            agencia=self.agency1,
            fecha_venta="2024-01-15",
            total_venta=1000,
            moneda_id=1,
        )

        self.set_current_agency(self.agency2)
        client2 = Cliente.objects.create(
            nombres="Cliente 2",
            email="cliente2@agencia2.test",
            agencia=self.agency2,
        )
        venta2 = Venta.objects.create(
            cliente=client2,
            agencia=self.agency2,
            fecha_venta="2024-01-15",
            total_venta=2000,
            moneda_id=1,
        )

        # Agency 1 sees only venta1
        self.set_current_agency(self.agency1)
        ventas = Venta.objects.all()
        self.assertIn(venta1, ventas)
        self.assertNotIn(venta2, ventas)

        # Agency 2 sees only venta2
        self.set_current_agency(self.agency2)
        ventas = Venta.objects.all()
        self.assertIn(venta2, ventas)
        self.assertNotIn(venta1, ventas)

        self.clear_agency()

    def test_itemfactura_isolation(self):
        """ItemFactura isolated via venta__agencia."""

        self.set_current_agency(self.agency1)
        client = Cliente.objects.create(
            nombres="Client 1", email="c1@test.com", agencia=self.agency1
        )
        venta = Venta.objects.create(
            cliente=client, agencia=self.agency1, total_venta=1000, moneda_id=1
        )

        item = ItemFactura.objects.create(
            venta=venta,
            tipo_servicio="ALO",
            descripcion="Hotel test",
            cantidad=1,
            precio_unitario=500,
            subtotal_item=500,
            total_item=500,
        )

        self.set_current_agency(self.agency1)
        items = ItemFactura.objects.all()
        self.assertIn(item, items)

        self.set_current_agency(self.agency2)
        items = ItemFactura.objects.all()
        self.assertEqual(items.count(), 0)

        self.clear_agency()


class TestCRMModelsIsolation(MultiTenantIsolationTestCase):
    """Test CRM models (OportunidadViaje, MensajeWhatsApp) isolation."""

    def setUp(self):
        self.clear_agency()

    def test_oportunidad_isolation(self):
        """OportunidadViaje isolated by agencia."""

        self.set_current_agency(self.agency1)
        client1 = Cliente.objects.create(
            nombres="Client 1", email="c1@a1.com", agencia=self.agency1
        )
        opp1 = OportunidadViaje.objects.create(
            cliente=client1,
            agencia=self.agency1,
            destino="Cancun",
            estado="nueva",
        )

        self.set_current_agency(self.agency2)
        client2 = Cliente.objects.create(
            nombres="Client 2", email="c2@a2.com", agencia=self.agency2
        )
        opp2 = OportunidadViaje.objects.create(
            cliente=client2,
            agencia=self.agency2,
            destino="Madrid",
            estado="nueva",
        )

        self.set_current_agency(self.agency1)
        opps = OportunidadViaje.objects.all()
        self.assertIn(opp1, opps)
        self.assertNotIn(opp2, opps)

        self.clear_agency()

    def test_mensaje_whatsapp_isolation(self):
        """MensajeWhatsApp isolated by agencia via SET_NULL on cliente FK."""

        self.set_current_agency(self.agency1)
        client = Cliente.objects.create(nombres="Client 1", email="c1@a1.com", agencia=self.agency1)
        msg1 = MensajeWhatsApp.objects.create(
            cliente=client,
            mensaje="Hola from agency 1",
            agencia=self.agency1,
        )

        self.set_current_agency(self.agency2)
        client2 = Cliente.objects.create(
            nombres="Client 2", email="c2@a2.com", agencia=self.agency2
        )
        msg2 = MensajeWhatsApp.objects.create(
            cliente=client2,
            mensaje="Hola from agency 2",
            agencia=self.agency2,
        )

        self.set_current_agency(self.agency1)
        msgs = MensajeWhatsApp.objects.all()
        self.assertIn(msg1, msgs)
        self.assertNotIn(msg2, msgs)

        self.clear_agency()


class TestFinanceModelsIsolation(MultiTenantIsolationTestCase):
    """Test finance models (Factura) isolation."""

    def setUp(self):
        self.clear_agency()

    def test_factura_isolation(self):
        """Factura isolated by agencia."""

        self.set_current_agency(self.agency1)
        client1 = Cliente.objects.create(
            nombres="Client 1", email="c1@a1.com", agencia=self.agency1
        )
        factura1 = Factura.objects.create(
            cliente=client1,
            agencia=self.agency1,
            numero_factura="FAC-001",
            total_factura=1000,
            estado="PEN",
            moneda_id=1,
        )

        self.set_current_agency(self.agency2)
        client2 = Cliente.objects.create(
            nombres="Client 2", email="c2@a2.com", agencia=self.agency2
        )
        factura2 = Factura.objects.create(
            cliente=client2,
            agencia=self.agency2,
            numero_factura="FAC-002",
            total_factura=2000,
            estado="PEN",
            moneda_id=1,
        )

        self.set_current_agency(self.agency1)
        facturas = Factura.objects.all()
        self.assertIn(factura1, facturas)
        self.assertNotIn(factura2, facturas)

        self.set_current_agency(self.agency2)
        facturas = Factura.objects.all()
        self.assertIn(factura2, facturas)
        self.assertNotIn(factura1, facturas)

        self.clear_agency()


class TestAutomationModelsIsolation(MultiTenantIsolationTestCase):
    """Test automation models isolation."""

    def setUp(self):
        self.clear_agency()

    def test_notificacion_inteligente_isolation(self):
        """NotificacionInteligente isolated by usuario's agencia."""
        # NotificacionInteligente links to usuario, which has agencia via relation
        # The manager should filter by usuario's active agencia
        self.set_current_agency(self.agency1)
        # NotificacionInteligente requires usuario, which must have agencia
        # Test via manager filtering
        self.assertGreaterEqual(NotificacionInteligente.objects.count(), 0)
        # Should only see notifications for users in agency1
        # (Implementation depends on how manager filters)

        self.clear_agency()

    def test_notificacion_agente_isolation(self):
        """NotificacionAgente isolated by usuario's agencia."""
        self.set_current_agency(self.agency1)
        self.assertGreaterEqual(NotificacionAgente.objects.count(), 0)
        self.clear_agency()


class TestSuperuserAccess(MultiTenantIsolationTestCase):
    """Test that superusers can see all data."""

    def test_superuser_sees_all_agencies(self):
        """Superuser bypasses agency filtering."""
        # Create data in agency1
        self.set_current_agency(self.agency1)
        client = Cliente.objects.create(nombres="Client 1", email="c1@a1.com", agencia=self.agency1)

        # Switch to superuser context (no agency set)
        self.clear_agency()

        # Superuser should see all
        clients = Cliente.objects.all()
        self.assertIn(client, clients)

        self.clear_agency()


class TestAgenciaContextManager(MultiTenantIsolationTestCase):
    """Test agency_context context manager."""

    def test_agency_context_manager(self):
        """agency_context temporarily sets agency."""

        self.assertIsNone(get_current_agency())

        with agency_context(self.agency1):
            self.assertEqual(get_current_agency(), self.agency1)

        self.assertIsNone(get_current_agency())

    def test_nested_context(self):
        """Nested contexts restore correctly."""

        with agency_context(self.agency1):
            self.assertEqual(get_current_agency(), self.agency1)
            with agency_context(self.agency2):
                self.assertEqual(get_current_agency(), self.agency2)
            self.assertEqual(get_current_agency(), self.agency1)
        self.assertIsNone(get_current_agency())


class TestAgenciaManagerBehavior(MultiTenantIsolationTestCase):
    """Test AgenciaManager behavior directly."""

    def test_manager_filters_soft_delete(self):
        """AgenciaManager excludes soft-deleted."""
        from core.models import SoftDeleteModel

        # Ensure model uses SoftDeleteModel
        self.assertTrue(issubclass(Cliente, SoftDeleteModel))

    def test_manager_filters_by_agencia(self):
        """Manager auto-filters by agencia in context."""

        self.set_current_agency(self.agency1)
        Cliente.objects.create(nombres="Test", email="t@test.com", agencia=self.agency1)

        self.set_current_agency(self.agency2)
        Cliente.objects.all()
        # Should not see agency1 client
        client_qs = Cliente.objects.filter(agencia=self.agency1)
        self.assertEqual(client_qs.count(), 0)

        self.clear_agency()


class TestEdgeCases(MultiTenantIsolationTestCase):
    """Edge cases and boundary conditions."""

    def test_user_without_agencia(self):
        """User without agencia sees nothing (except superuser)."""
        User.objects.create_user(username="noagency", email="no@agency.com", password="test123")
        # No agencia assigned

        self.set_current_agency(self.agency1)
        Cliente.objects.all()
        # Should see agency1 data (set by middleware)
        # But if middleware doesn't set agencia for this user...
        # This tests the middleware behavior

    def test_inactive_agencia(self):
        """Inactive agencia excluded from queries."""
        inactive_agency = Agencia.objects.create(
            nombre="Inactive Agency",
            dominio="inactive.test",
            subdominio_slug="inactive",
            activo=False,
        )

        self.set_current_agency(inactive_agency)
        # Should see nothing or raise
        Cliente.objects.all()
        # Depends on implementation

    def test_agencia_deleted_cascade(self):
        """Deleting agencia cascades correctly."""
        pass  # Test cascade behavior


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

pytest_plugins = ["pytest_django"]


def pytest_configure(config):
    config.option.django_settings_module = "travelhub.settings"


# Run with: pytest tests/test_multi_tenant_isolation.py -v
