from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models.agencia import Agencia, UsuarioAgencia
from core.models.audit import AuditLog


class TestAuditTimelineView(TestCase):
    """
    🛡️ Test Suite para Módulo 3: Audit Log Visual Timeline
    Garantiza el correcto funcionamiento de la Bóveda de Auditoría Forense,
    el aislamiento por tenant (Agencias) y los filtros en tiempo real.
    """

    def setUp(self):
        # Desactivar tareas de Celery reales
        patcher = patch("core.tasks.migrar_logos_agencia_task.delay")
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        # Crear Agencias
        self.agencia_a = Agencia.objects.create(
            nombre="Agencia Audit A", rif="J-44444444-4", activa=True
        )
        self.agencia_b = Agencia.objects.create(
            nombre="Agencia Audit B", rif="J-55555555-5", activa=True
        )

        # Crear Usuarios
        self.user_a = User.objects.create_user(username="usera", password="password1")  # noqa: S106
        self.user_b = User.objects.create_user(username="userb", password="password1")  # noqa: S106

        # Asignar a Agencias
        UsuarioAgencia.objects.create(
            usuario=self.user_a, agencia=self.agencia_a, rol="gerente", activo=True
        )
        UsuarioAgencia.objects.create(
            usuario=self.user_b, agencia=self.agencia_b, rol="gerente", activo=True
        )

        # Crear Logs de Auditoría para Agencia A
        self.log_a1 = AuditLog.objects.create(
            modelo="Venta",
            object_id="1",
            accion="CREATE",
            agencia=self.agencia_a,
            descripcion="Venta creada por IA",
            user=self.user_a,
        )
        self.log_a2 = AuditLog.objects.create(
            modelo="Factura",
            object_id="2",
            accion="UPDATE",
            agencia=self.agencia_a,
            descripcion="Factura modificada manualmente",
            user=self.user_a,
        )

        # Crear Logs de Auditoría para Agencia B
        self.log_b = AuditLog.objects.create(
            modelo="Venta",
            object_id="99",
            accion="DELETE",
            agencia=self.agencia_b,
            descripcion="Venta eliminada",
            user=self.user_b,
        )

    def test_audit_timeline_requires_login(self):
        """Verifica que el panel de auditoría requiera inicio de sesión."""
        response = self.client.get(reverse("finance:audit_timeline"), secure=True)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_audit_timeline_tenant_isolation(self):
        """Verifica el aislamiento: el usuario de Agencia A no ve registros de Agencia B."""
        self.client.force_login(self.user_a)
        response = self.client.get(reverse("finance:audit_timeline"), secure=True)
        self.assertEqual(response.status_code, 200)
        logs_in_context = response.context["logs"]
        self.assertIn(self.log_a1, logs_in_context)
        self.assertIn(self.log_a2, logs_in_context)
        self.assertNotIn(self.log_b, logs_in_context)

    def test_audit_timeline_filtering(self):
        """Prueba los filtros de búsqueda por acción, entidad o término de descripción."""
        self.client.force_login(self.user_a)

        # Filtrar por Acción CREATE
        response = self.client.get(
            reverse("finance:audit_timeline"), {"accion": "CREATE"}, secure=True
        )
        self.assertEqual(response.status_code, 200)
        logs = response.context["logs"]
        self.assertIn(self.log_a1, logs)
        self.assertNotIn(self.log_a2, logs)

        # Filtrar por Entidad Factura
        response = self.client.get(
            reverse("finance:audit_timeline"), {"modelo": "Factura"}, secure=True
        )
        self.assertEqual(response.status_code, 200)
        logs = response.context["logs"]
        self.assertIn(self.log_a2, logs)
        self.assertNotIn(self.log_a1, logs)

        # Filtrar por texto 'modificada'
        response = self.client.get(
            reverse("finance:audit_timeline"), {"q": "modificada"}, secure=True
        )
        self.assertEqual(response.status_code, 200)
        logs = response.context["logs"]
        self.assertIn(self.log_a2, logs)
        self.assertNotIn(self.log_a1, logs)
