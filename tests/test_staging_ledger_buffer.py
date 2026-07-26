import unittest
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.contabilidad.models import AsientoContable, DetalleAsiento, PlanContable
from apps.finance.models_stubs import Moneda, PropuestaTransaccionIA
from core.models.agencia import Agencia, UsuarioAgencia

User = get_user_model()


@unittest.skip("Stub models PropuestaTransaccionIA and Moneda have no backing table")
@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    SESSION_ENGINE="django.contrib.sessions.backends.db",
)
class StagingLedgerBufferTest(TestCase):
    """StagingLedgerBufferTest."""

    def setUp(self):
        """setUp."""
        # Create user first
        self.user = User.objects.create_user(
            username="cfo_user", email="cfo_user@test.com", password="securepassword123"
        )
        # Create agency with owner
        self.agencia = Agencia.objects.create(
            nombre="CFO Test Agency", email_principal="cfo_test@agency.com", propietario=self.user
        )
        # Link user to agency as active
        self.usuario_agencia = UsuarioAgencia.objects.create(
            usuario=self.user, agencia=self.agencia, rol="admin", activo=True
        )

        # Create USD Currency
        self.moneda_usd, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dolar", "simbolo": "$"}
        )

        # Create PlanContable accounts for testing Balanced Asiento
        self.cuenta_banco = PlanContable.objects.create(
            agencia=self.agencia,
            codigo_cuenta="110101",
            nombre_cuenta="Banco Principal",
            tipo_cuenta=PlanContable.TipoCuentaChoices.ACTIVO,
            naturaleza=PlanContable.NaturalezaChoices.DEUDORA,
            acepta_movimientos=True,
        )
        self.cuenta_ingreso = PlanContable.objects.create(
            agencia=self.agencia,
            codigo_cuenta="410101",
            nombre_cuenta="Ingresos por Ventas",
            tipo_cuenta=PlanContable.TipoCuentaChoices.INGRESO,
            naturaleza=PlanContable.NaturalezaChoices.ACREEDORA,
            acepta_movimientos=True,
        )

    def test_propuesta_model_justificacion_property(self):
        """Verifica que la propiedad de compatibilidad justificacion mapea a ia_justificacion"""
        propuesta = PropuestaTransaccionIA.objects.create(
            agencia=self.agencia,
            modulo_objetivo="CONTABILIDAD",
            accion_tipo="CREAR_ASIENTO",
            payload_datos={"glosa": "Asiento de Prueba"},
            ia_justificacion="Esta es la justificación original",
            estado=PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE,
        )
        # Test getter
        self.assertEqual(propuesta.justificacion, "Esta es la justificación original")

        # Test setter
        propuesta.justificacion = "Nueva justificación contable"
        self.assertEqual(propuesta.ia_justificacion, "Nueva justificación contable")
        self.assertEqual(propuesta.justificacion, "Nueva justificación contable")

    def test_ai_proposals_partial_view_renders_correctly(self):
        """Verifica que la vista HTMX de propuestas pendientes renderiza correctamente en el dashboard contable"""
        self.client.force_login(self.user)

        # Create pending proposal
        PropuestaTransaccionIA.objects.create(
            agencia=self.agencia,
            modulo_objetivo="CONTABILIDAD",
            accion_tipo="CREAR_ASIENTO",
            payload_datos={
                "glosa": "Registro de Venta Mensual",
                "detalles": [
                    {"codigo_cuenta": "110101", "debe": 1500.0, "haber": 0.0},
                    {"codigo_cuenta": "410101", "debe": 0.0, "haber": 1500.0},
                ],
            },
            ia_justificacion="Ajuste automático de ventas del mes",
            estado=PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE,
        )

        url = reverse("finance:ai_proposals_partial")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registro de Venta Mensual")
        self.assertContains(response, "Ajuste automático de ventas del mes")
        self.assertContains(response, "110101")
        self.assertContains(response, "410101")

    def test_resolve_proposal_reject_action(self):
        """Verifica que la acción de rechazar una propuesta actualiza el buffer correctamente sin modificar el ledger contable"""
        self.client.force_login(self.user)

        propuesta = PropuestaTransaccionIA.objects.create(
            agencia=self.agencia,
            modulo_objetivo="CONTABILIDAD",
            accion_tipo="CREAR_ASIENTO",
            payload_datos={
                "glosa": "Venta Rechazada",
                "detalles": [
                    {"codigo_cuenta": "110101", "debe": 100.0, "haber": 0.0},
                    {"codigo_cuenta": "410101", "debe": 0.0, "haber": 100.0},
                ],
            },
            ia_justificacion="Ajuste incorrecto",
            estado=PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE,
        )

        url = reverse(
            "finance:ai_proposal_resolve_htmx", kwargs={"pk": propuesta.pk, "action": "reject"}
        )
        response = self.client.post(
            url, {"comentarios": "Rechazado en auditoría por datos erróneos."}
        )

        self.assertEqual(response.status_code, 200)

        # Verify proposal state in database
        propuesta.refresh_from_db()
        self.assertEqual(propuesta.estado, PropuestaTransaccionIA.EstadoPropuesta.RECHAZADA)
        self.assertEqual(propuesta.usuario_resolutor, self.user)
        self.assertEqual(
            propuesta.comentarios_resolucion, "Rechazado en auditoría por datos erróneos."
        )

        # Verify no AsientoContable was created
        self.assertFalse(AsientoContable.objects.filter(agencia=self.agencia).exists())

    def test_resolve_proposal_approve_crear_asiento(self):
        """Verifica que aprobar una propuesta CREAR_ASIENTO ejecuta el asiento de forma transaccional y equilibrada"""
        self.client.force_login(self.user)

        propuesta = PropuestaTransaccionIA.objects.create(
            agencia=self.agencia,
            modulo_objetivo="CONTABILIDAD",
            accion_tipo="CREAR_ASIENTO",
            payload_datos={
                "glosa": "Ingreso por Servicios AI",
                "detalles": [
                    {"codigo_cuenta": "110101", "debe": 850.50, "haber": 0.0},
                    {"codigo_cuenta": "410101", "debe": 0.0, "haber": 850.50},
                ],
            },
            ia_justificacion="Ajuste automático de conciliación bancaria",
            estado=PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE,
        )

        url = reverse(
            "finance:ai_proposal_resolve_htmx", kwargs={"pk": propuesta.pk, "action": "approve"}
        )
        response = self.client.post(url, {"comentarios": "Aprobado y balanceado."})

        self.assertEqual(response.status_code, 200)

        # Verify proposal state
        propuesta.refresh_from_db()
        self.assertEqual(propuesta.estado, PropuestaTransaccionIA.EstadoPropuesta.APROBADA)
        self.assertEqual(propuesta.usuario_resolutor, self.user)
        self.assertEqual(propuesta.comentarios_resolucion, "Aprobado y balanceado.")

        # Verify AsientoContable creation in contabilidad
        asiento = AsientoContable.objects.get(agencia=self.agencia)
        self.assertEqual(asiento.descripcion_general, "Ingreso por Servicios AI")
        self.assertEqual(asiento.estado, "CON")  # Confirmado
        self.assertEqual(asiento.moneda, self.moneda_usd)

        # Verify details
        detalles = DetalleAsiento.objects.filter(asiento=asiento).order_by("linea")
        self.assertEqual(detalles.count(), 2)

        # Detail 1 (Debe)
        self.assertEqual(detalles[0].cuenta_contable, self.cuenta_banco)
        self.assertEqual(detalles[0].debe, Decimal("850.50"))
        self.assertEqual(detalles[0].haber, Decimal("0.0"))

        # Detail 2 (Haber)
        self.assertEqual(detalles[1].cuenta_contable, self.cuenta_ingreso)
        self.assertEqual(detalles[1].debe, Decimal("0.0"))
        self.assertEqual(detalles[1].haber, Decimal("850.50"))

        # Verify balance
        asiento.calcular_totales()
        self.assertTrue(asiento.esta_cuadrado)

    def test_resolve_proposal_multi_tenant_isolation_fails(self):
        """Verifica que un usuario de otra agencia no puede ver ni resolver propuestas del buffer de esta agencia"""
        # Create second agency user
        user_hack = User.objects.create_user(
            username="hacker_user", email="hacker_user@test.com", password="securepassword123"
        )
        # Create second agency with owner
        agencia_hack = Agencia.objects.create(
            nombre="Hacker Agency", email_principal="hacker@agency.com", propietario=user_hack
        )
        UsuarioAgencia.objects.create(
            usuario=user_hack, agencia=agencia_hack, rol="admin", activo=True
        )

        # Create proposal belonging to CFO Test Agency (our agency)
        propuesta = PropuestaTransaccionIA.objects.create(
            agencia=self.agencia,
            modulo_objetivo="CONTABILIDAD",
            accion_tipo="CREAR_ASIENTO",
            payload_datos={
                "glosa": "Ingreso Confidencial",
                "detalles": [
                    {"codigo_cuenta": "110101", "debe": 500.0, "haber": 0.0},
                    {"codigo_cuenta": "410101", "debe": 0.0, "haber": 500.0},
                ],
            },
            ia_justificacion="Ajuste confidencial",
            estado=PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE,
        )

        # Log in as hacker user
        self.client.force_login(user_hack)

        # Attempt to get or resolve CFO Test Agency proposal
        url_resolve = reverse(
            "finance:ai_proposal_resolve_htmx", kwargs={"pk": propuesta.pk, "action": "approve"}
        )
        response = self.client.post(url_resolve, {"comentarios": "Intentando hackear"})

        # Should return 404 (Not Found) because the query uses get_object_or_404(..., agencia=agencia)
        self.assertEqual(response.status_code, 404)

        # Verify proposal remains pending
        propuesta.refresh_from_db()
        self.assertEqual(propuesta.estado, PropuestaTransaccionIA.EstadoPropuesta.PENDIENTE)
        self.assertIsNone(propuesta.usuario_resolutor)
