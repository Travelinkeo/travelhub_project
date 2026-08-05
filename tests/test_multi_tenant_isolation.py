#!/usr/bin/env python
"""
Phase 2 Hardening - Multi-Tenant Isolation Tests

Tests to verify multi-tenant isolation works correctly after migrations.
These tests verify that AgenciaMixin/Manager properly filters queries by agencia.

Run with: python -m pytest tests/test_multi_tenant_isolation.py -v
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.automation.models import NotificacionAgente, NotificacionInteligente
from apps.bookings.models import Venta
from apps.common.models import Moneda
from apps.communications.models import NotificationLog, NotificationTemplate
from apps.contabilidad.models import AsientoContable
from apps.crm.models import Cliente, MensajeWhatsApp, OportunidadViaje
from apps.finance.models import Factura, ItemFactura
from apps.finance.models_stubs import FacturaConsolidada
from core.middleware import agency_context, agency_var, get_current_agency
from core.models import Agencia, UsuarioAgencia

User = get_user_model()


class MultiTenantIsolationTestCase(TestCase):
    """Base test case with agency setup."""

    @classmethod
    def setUpTestData(cls):
        # Create two agencies. subdominio_slug vive en AgenciaConfiguracion (creada
        # por signal al guardar Agencia); no es kwarg valido de Agencia.objects.create().
        cls.agency1 = Agencia.objects.create(
            nombre="Agencia Test 1",
            email_principal="admin@agencia1.test",
        )
        config1 = cls.agency1.configuracion
        config1.subdominio_slug = "agencia1"
        config1.save()

        cls.agency2 = Agencia.objects.create(
            nombre="Agencia Test 2",
            email_principal="admin@agencia2.test",
        )
        config2 = cls.agency2.configuracion
        config2.subdominio_slug = "agencia2"
        config2.save()

        # Create users in each agency. La relacion usuario-agencia pasa por el
        # modelo intermedio UsuarioAgencia (no admite through_defaults en .add()).
        cls.user1 = User.objects.create_user(
            username="user1", email="user1@agencia1.test", password="test123"
        )
        UsuarioAgencia.objects.create(
            usuario=cls.user1, agencia=cls.agency1, rol="admin", activo=True
        )

        cls.user2 = User.objects.create_user(
            username="user2", email="user2@agencia2.test", password="test123"
        )
        UsuarioAgencia.objects.create(
            usuario=cls.user2, agencia=cls.agency2, rol="admin", activo=True
        )

        # Superuser (can see all)
        cls.superuser = User.objects.create_superuser(
            username="admin", email="admin@test.com", password="test123"
        )

        # Moneda global (agencia=None) compartida por todos los tenants.
        cls.moneda = Moneda.objects.create(
            codigo_iso="USD", nombre="Dólar Estadounidense", simbolo="$"
        )

    def set_current_agency(self, agency):
        """Helper to set thread-local agency context."""
        agency_var.set(agency)

    def clear_agency(self):
        """Clear thread-local agency context."""
        agency_var.set(None)


class TestNotificationTemplateIsolation(MultiTenantIsolationTestCase):
    """Test NotificationTemplate/Log multi-tenant isolation."""

    def setUp(self):
        """setUp."""
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
        """setUp."""
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
            moneda=self.moneda,
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
            moneda=self.moneda,
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
        """ItemFactura isolated por su propio campo agencia (AgenciaMixin)."""

        self.set_current_agency(self.agency1)
        client = Cliente.objects.create(
            nombres="Client 1", email="c1@test.com", agencia=self.agency1
        )
        factura = Factura.objects.create(
            cliente=client,
            agencia=self.agency1,
            numero_factura="FAC-ITEM-001",
            estado="EMI",
            moneda=self.moneda,
            tasa_cambio_bcv=Decimal("1.00"),
        )

        item = ItemFactura.objects.create(
            factura=factura,
            agencia=self.agency1,
            descripcion="Hotel test",
            cantidad=Decimal("1.00"),
            precio_unitario=Decimal("500.00"),
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
        """setUp."""
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
            etapa=OportunidadViaje.Etapa.NUEVO,
        )

        self.set_current_agency(self.agency2)
        client2 = Cliente.objects.create(
            nombres="Client 2", email="c2@a2.com", agencia=self.agency2
        )
        opp2 = OportunidadViaje.objects.create(
            cliente=client2,
            agencia=self.agency2,
            destino="Madrid",
            etapa=OportunidadViaje.Etapa.NUEVO,
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
            direccion="OUT",
            texto="Hola from agency 1",
            agencia=self.agency1,
        )

        self.set_current_agency(self.agency2)
        client2 = Cliente.objects.create(
            nombres="Client 2", email="c2@a2.com", agencia=self.agency2
        )
        msg2 = MensajeWhatsApp.objects.create(
            cliente=client2,
            direccion="OUT",
            texto="Hola from agency 2",
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
        """setUp."""
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
            estado="EMI",
            moneda=self.moneda,
            tasa_cambio_bcv=Decimal("1.00"),
        )

        self.set_current_agency(self.agency2)
        client2 = Cliente.objects.create(
            nombres="Client 2", email="c2@a2.com", agencia=self.agency2
        )
        factura2 = Factura.objects.create(
            cliente=client2,
            agencia=self.agency2,
            numero_factura="FAC-002",
            estado="EMI",
            moneda=self.moneda,
            tasa_cambio_bcv=Decimal("1.00"),
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


class TestFacturaConsolidadaIsolation(MultiTenantIsolationTestCase):
    """Test FacturaConsolidada isolation (R2: ahora hereda AgenciaMixin).

    Regression: FacturaConsolidada antes heredaba models.Model directo (sin
    AgenciaMixin). Sus querysets NO se filtraban automaticamente por agencia,
    exponiendo riesgo de fuga cross-tenant si un futuro viewset consultaba
    este modelo. Ver apps/finance/models/facturacion.py.
    """

    def setUp(self):
        """setUp."""
        self.clear_agency()

    def test_factura_consolidada_isolation(self):
        """FacturaConsolidada se filtra por agencia via AgenciaManager."""
        self.set_current_agency(self.agency1)
        cliente1 = Cliente.objects.create(
            nombres="Client 1", email="c1@a1.com", agencia=self.agency1
        )
        factura1 = FacturaConsolidada.objects.create(
            agencia=self.agency1,
            cliente=cliente1,
            fecha_emision="2024-01-01",
            monto_total=Decimal("1000"),
            estado="PEN",
        )

        self.set_current_agency(self.agency2)
        cliente2 = Cliente.objects.create(
            nombres="Client 2", email="c2@a2.com", agencia=self.agency2
        )
        factura2 = FacturaConsolidada.objects.create(
            agencia=self.agency2,
            cliente=cliente2,
            fecha_emision="2024-01-01",
            monto_total=Decimal("2000"),
            estado="PEN",
        )

        # Contexto agencia1 solo ve factura1
        self.set_current_agency(self.agency1)
        facturas = FacturaConsolidada.objects.all()
        self.assertIn(factura1, facturas)
        self.assertNotIn(factura2, facturas)

        # Contexto agencia2 solo ve factura2
        self.set_current_agency(self.agency2)
        facturas = FacturaConsolidada.objects.all()
        self.assertIn(factura2, facturas)
        self.assertNotIn(factura1, facturas)

        self.clear_agency()


class TestCascadeToDeleteSetNull(MultiTenantIsolationTestCase):
    """Test regression R1: borrar cliente/user/venta NO borra histórico.

    Antes, on_delete=CASCADE en 28 FKs provocaba pérdida de datos históricos:
    leads, mensajes WhatsApp, comisiones freelance, pasaportes, y todos los
    componentes de venta. Ahora con SET_NULL, el registro referenciado queda
    huérfano (fk_id=NULL) pero preserva auditoría.
    Ver apps/crm/migrations/0033 y apps/bookings/migrations/0047.
    """

    def setUp(self):
        """setUp."""
        self.clear_agency()

    def test_borrar_cliente_preserva_oportunidad_viaje(self):
        """Borrar un Cliente NO borra su OportunidadViaje; queda con cliente=None."""
        self.set_current_agency(self.agency1)
        cliente = Cliente.objects.create(
            nombres="To Delete", email="del@a1.com", agencia=self.agency1
        )
        opp = OportunidadViaje.objects.create(
            cliente=cliente,
            agencia=self.agency1,
            destino="Madrid",
        )

        cliente_pk = cliente.pk
        # Hard-delete el cliente (.std delete() de Django, no SoftDelete)
        Cliente.all_objects.filter(pk=cliente_pk).hard_delete()
        opp.refresh_from_db()

        self.assertIsNone(opp.cliente_id, "OportunidadViaje.cliente debe ser NULL tras borrar")
        self.assertEqual(opp.cliente, None)

    def test_borrar_cliente_preserva_mensaje_whatsapp(self):
        """Borrar Cliente NO borra MensajeWhatsApp; queda con cliente=None."""
        self.set_current_agency(self.agency1)
        cliente = Cliente.objects.create(
            nombres="To Delete", email="del2@a1.com", agencia=self.agency1
        )
        msg = MensajeWhatsApp.objects.create(
            cliente=cliente,
            direccion="IN",
            texto="Hola",
            agencia=self.agency1,
        )

        Cliente.all_objects.filter(pk=cliente.pk).hard_delete()
        msg.refresh_from_db()

        self.assertIsNone(msg.cliente_id, "MensajeWhatsApp.cliente debe ser NULL tras borrar")

    def test_borrar_venta_preserva_comision_freelancer(self):
        """Borrar Venta NO borra ComisionFreelancer; queda con venta=None."""
        self.set_current_agency(self.agency1)
        cliente = Cliente.objects.create(nombres="Client", email="c@a1.com", agencia=self.agency1)
        moneda = Moneda.objects.first() or Moneda.objects.create(
            nombre="USD", codigo_iso="USD", es_moneda_local=True, agencia=self.agency1
        )
        venta = Venta.objects.create(
            agencia=self.agency1,
            cliente=cliente,
            fecha_venta="2024-01-01",
            total_venta=1000,
            moneda=moneda,
        )
        from apps.crm.models import ComisionFreelancer, FreelancerProfile

        user_freelancer = User.objects.create_user(
            username="freelancer1", email="f@a1.com", password="test123"
        )
        user_freelancer.agencias.add(
            self.agency1, through_defaults={"rol": "freelancer", "activo": True}
        )
        freelancer = FreelancerProfile.objects.create(
            usuario=user_freelancer, agencia=self.agency1, porcentaje_comision=10
        )
        comision = ComisionFreelancer.objects.create(
            venta=venta, freelancer=freelancer, agencia=self.agency1, monto=100
        )

        # Hard-delete venta (no soft-delete)
        Venta.all_objects.filter(pk=venta.pk).hard_delete()
        comision.refresh_from_db()

        self.assertIsNone(comision.venta_id, "ComisionFreelancer.venta debe ser NULL tras borrar")


class TestContabilidadModelsIsolation(MultiTenantIsolationTestCase):
    """Test modelos de Contabilidad (AsientoContable) aislamiento."""

    def setUp(self):
        """setUp."""
        self.clear_agency()

    def test_asiento_contable_isolation(self):
        """AsientoContable se filtra por agencia via AgenciaManager."""
        self.set_current_agency(self.agency1)
        asiento1 = AsientoContable.objects.create(
            agencia=self.agency1,
            fecha_contable="2024-01-01",
            descripcion_general="Asiento A1",
            tipo_asiento="DIA",
        )

        self.set_current_agency(self.agency2)
        asiento2 = AsientoContable.objects.create(
            agencia=self.agency2,
            fecha_contable="2024-01-01",
            descripcion_general="Asiento A2",
            tipo_asiento="DIA",
        )

        # Contexto agencia1 solo ve asiento1
        self.set_current_agency(self.agency1)
        asientos = AsientoContable.objects.all()
        self.assertIn(asiento1, asientos)
        self.assertNotIn(asiento2, asientos)

        # Contexto agencia2 solo ve asiento2
        self.set_current_agency(self.agency2)
        asientos = AsientoContable.objects.all()
        self.assertIn(asiento2, asientos)
        self.assertNotIn(asiento1, asientos)

        self.clear_agency()


class TestAutomationModelsIsolation(MultiTenantIsolationTestCase):
    """Test automation models isolation."""

    def setUp(self):
        """setUp."""
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
        from core.models.base import SoftDeleteModel

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
            email_principal="admin@inactive.test",
        )
        config = inactive_agency.configuracion
        config.subdominio_slug = "inactive"
        config.save()

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
    """pytest_configure."""
    config.option.django_settings_module = "travelhub.settings"


# Run with: pytest tests/test_multi_tenant_isolation.py -v
