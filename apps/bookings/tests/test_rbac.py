from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.module_loading import import_string

from apps.bookings.models import Venta
from core.models.agencia import Agencia, UsuarioAgencia

Moneda = import_string("apps.finance.models.currencies.Moneda")
Factura = import_string("apps.finance.models.Factura")


class RBACSecurityTest(TestCase):
    """
    🛡️ Test Suite para Módulo 3: RBAC (Role-Based Access Control)
    Garantiza que los roles de Vendedor, Contador, Supervisor (Gerente) y Consulta
    tengan el aislamiento y los límites de acción correctos sobre operaciones y finanzas.
    """

    def setUp(self):
        # Desactivar tareas de Celery reales
        patcher = patch("core.tasks.migrar_logos_agencia_task.delay")
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        # Crear Agencia y Moneda
        self.agencia = Agencia.objects.create(
            nombre="Agencia RBAC", rif="J-33333333-3", activa=True
        )
        self.moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )

        # Crear Usuarios
        self.user_vendedor_1 = User.objects.create_user(username="vendedor1", password="password1")  # noqa: S106
        self.user_vendedor_2 = User.objects.create_user(username="vendedor2", password="password1")  # noqa: S106
        self.user_gerente = User.objects.create_user(username="gerente", password="password1")  # noqa: S106
        self.user_contador = User.objects.create_user(username="contador", password="password1")  # noqa: S106
        self.user_consulta = User.objects.create_user(username="consulta", password="password1")  # noqa: S106

        # Asociar Roles
        UsuarioAgencia.objects.create(
            usuario=self.user_vendedor_1, agencia=self.agencia, rol="vendedor", activo=True
        )
        UsuarioAgencia.objects.create(
            usuario=self.user_vendedor_2, agencia=self.agencia, rol="vendedor", activo=True
        )
        UsuarioAgencia.objects.create(
            usuario=self.user_gerente, agencia=self.agencia, rol="gerente", activo=True
        )
        UsuarioAgencia.objects.create(
            usuario=self.user_contador, agencia=self.agencia, rol="contador", activo=True
        )
        UsuarioAgencia.objects.create(
            usuario=self.user_consulta, agencia=self.agencia, rol="consulta", activo=True
        )

        # Crear Venta para Vendedor 1
        with patch("core.models.base.get_current_agency", return_value=self.agencia):
            self.venta_vendedor_1 = Venta.objects.create(
                localizador="PNR-VEND1",
                moneda=self.moneda,
                subtotal=Decimal("100.00"),
                creado_por=self.user_vendedor_1,
            )

            # Crear Factura asociada para probar flujo de facturación
            self.factura = Factura.objects.create(
                venta_asociada=self.venta_vendedor_1,
                moneda=self.moneda,
                subtotal=Decimal("100.00"),
                tasa_cambio_bcv=Decimal("36.00"),
            )

    def test_vendedor_can_only_see_own_operations(self):
        """Vendedor 1 ve sus propias ventas, pero Vendedor 2 no puede verlas en los listados."""
        # Vendedor 1
        self.client.force_login(self.user_vendedor_1)
        response = self.client.get(reverse("bookings:venta_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.venta_vendedor_1, response.context["ventas"])

        # Vendedor 2
        self.client.force_login(self.user_vendedor_2)
        response = self.client.get(reverse("bookings:venta_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.venta_vendedor_1, response.context["ventas"])

    def test_vendedor_cannot_access_others_operation_detail_or_update(self):
        """Vendedor 2 recibe 404 al intentar acceder o editar la venta de Vendedor 1."""
        self.client.force_login(self.user_vendedor_2)

        # Detalle
        response = self.client.get(
            reverse("bookings:venta_detail", kwargs={"pk": self.venta_vendedor_1.pk})
        )
        self.assertEqual(response.status_code, 404)

        # Formulario de Edición (GET)
        response = self.client.get(
            reverse("bookings:venta_update", kwargs={"pk": self.venta_vendedor_1.pk})
        )
        self.assertEqual(response.status_code, 404)

        # Guardar Edición (POST)
        response = self.client.post(
            reverse("bookings:venta_update", kwargs={"pk": self.venta_vendedor_1.pk}),
            {"estado": "PAG"},
        )
        self.assertEqual(response.status_code, 404)

    def test_vendedor_can_update_own_operation(self):
        """Vendedor 1 puede editar su propia venta."""
        self.client.force_login(self.user_vendedor_1)
        response = self.client.get(
            reverse("bookings:venta_update", kwargs={"pk": self.venta_vendedor_1.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_consulta_role_is_strictly_read_only(self):
        """Rol Consulta puede leer ventas y detalles, pero se le prohíbe escribir (POST)."""
        self.client.force_login(self.user_consulta)

        # Leer listado y detalle
        response = self.client.get(reverse("bookings:venta_list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse("bookings:venta_detail", kwargs={"pk": self.venta_vendedor_1.pk})
        )
        self.assertEqual(response.status_code, 200)

        # Modificación de Venta bloqueada
        response = self.client.post(
            reverse("bookings:venta_update", kwargs={"pk": self.venta_vendedor_1.pk}),
            {"estado": "PAG"},
        )
        self.assertEqual(response.status_code, 403)

    def test_contador_can_modify_billing_but_not_operations(self):
        """Contador no puede editar ventas operacionales pero sí puede modificar facturación/gastos."""
        self.client.force_login(self.user_contador)

        # Modificación de Venta bloqueada
        response = self.client.post(
            reverse("bookings:venta_update", kwargs={"pk": self.venta_vendedor_1.pk}),
            {"estado": "PAG"},
        )
        self.assertEqual(response.status_code, 403)

        # Modificación de Factura permitida
        response = self.client.post(
            reverse("finance:invoice_update", kwargs={"pk": self.factura.pk}),
            {"notas": "Notas actualizadas por Contador"},
        )
        self.assertEqual(response.status_code, 200)

    def test_gerente_has_full_access(self):
        """Gerente puede ver y editar cualquier venta dentro de la agencia."""
        self.client.force_login(self.user_gerente)

        # Detalle permitido
        response = self.client.get(
            reverse("bookings:venta_detail", kwargs={"pk": self.venta_vendedor_1.pk})
        )
        self.assertEqual(response.status_code, 200)

        # Edición permitida (GET)
        response = self.client.get(
            reverse("bookings:venta_update", kwargs={"pk": self.venta_vendedor_1.pk})
        )
        self.assertEqual(response.status_code, 200)
