"""
Tests de regresión para bugs IDOR documentados en CONTEXT_MAP.md.

Cubren:
  - P0-002: BoletoRetryParseAPIView (apps/bookings/views/boleto_views.py)
  - P0-003: VentaDoubleInvoiceAPIView (apps/finance/views/invoice_views.py)
            (vista realmente conectada en apps/finance/urls.py -> api_venta_double_invoice)

Precondición del sistema multi-tenant:
  `get_object_tenant_or_404(model, agencia, pk=...)` está diseñada a propósito
  para devolver **404 (no 403)** cuando un objeto existe pero pertenece a otra
  agencia, para no revelar su existencia a un atacante. Estos tests congelan
  ese comportamiento: si alguna vez vuelve a usarse `Venta.objects.get(pk=pk)`
  o `BoletoImportado.all_objects.get(pk=pk)` sin filtro de tenant, el status
  esperado pasaría a ser 200 (IDOR exitoso) y el test reventaría.
"""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.module_loading import import_string

from apps.bookings.models import BoletoImportado, Venta
from core.models.agencia import Agencia, UsuarioAgencia

Moneda = import_string("apps.common.models.Moneda")


def _silence_celery():
    """Silenciar el signal `migrar_logos_agencia_task.delay` que disparan las Agencia.save() en tests."""
    return patch("core.tasks.migrar_logos_agencia_task.delay")


class BoletoRetryParseIDORTest(TestCase):
    """
    P0-002: Un usuario de la Agencia Beta NO puede reintentar parseo de un
    boleto de la Agencia Alpha cambiando solo el pk de la URL.
    Esperado: 404, no 403 (no revelar existencia del objeto en otra agencia).
    """

    def setUp(self):
        """setUp."""
        patcher_delay = _silence_celery()
        self.mock_delay = patcher_delay.start()
        self.addCleanup(patcher_delay.stop)

        self.agencia_a = Agencia.objects.create(
            nombre="Agencia Alpha IDOR", rif="J-1000001-1", activa=True
        )
        self.agencia_b = Agencia.objects.create(
            nombre="Agencia Beta IDOR", rif="J-2000002-2", activa=True
        )
        self.moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )

        # Usuario perteneciente a la Agencia Beta (el atacante)
        self.user_b = User.objects.create_user(username="user_beta_idor", password="pw123")  # noqa: S106
        UsuarioAgencia.objects.create(
            usuario=self.user_b, agencia=self.agencia_b, rol="vendedor", activo=True
        )

        # Boleto de la Agencia Alpha (víctima). Se crea con all_objects + contexto
        # patcheado para evitar el candado de AgenciaManager que filtraría vacío.
        with patch("core.models.base.get_current_agency", return_value=self.agencia_a):
            self.boleto_alpha = BoletoImportado.all_objects.create(
                agencia=self.agencia_a,
                estado_parseo="PEN",
                log_parseo="boleto-Víctima",
                numero_boleto="TKT-ALPHA-001",
            )

    def test_usuario_beta_no_puede_reintentar_parseo_de_boleto_de_alpha(self):
        """
        Atacante pertenece a Agencia B intenta re-parsear boleto de Agencia A.
        Debe recibir 404, no 403, ni 200.
        """
        self.client.force_login(self.user_b)

        url = reverse("bookings:api_boleto_retry", kwargs={"pk": self.boleto_alpha.pk})

        # El flujo de Celery nunca debe ejecutarse porque get_object_tenant_or_404
        # corta antes. Aun así, silenciamos el helper por si una regresión lo invoca.
        with patch("apps.common.utils.celery_utils.safe_delay") as mock_safe_delay:
            response = self.client.post(url, secure=True)

        self.assertEqual(
            response.status_code,
            404,
            "IDOR NO corregido: un usuario de otra agencia pudo alcanzar el boleto.",
        )
        mock_safe_delay.assert_not_called()

    def test_usuario_alpha_si_puede_reintentar_parseo_de_su_propio_boleto(self):
        """Controles de sanity: el propietario sí alcanza su boleto (no rompimos acceso legítimo)."""
        user_a = User.objects.create_user(username="user_alpha_idor", password="pw123")  # noqa: S106
        UsuarioAgencia.objects.create(
            usuario=user_a, agencia=self.agencia_a, rol="vendedor", activo=True
        )
        self.client.force_login(user_a)

        url = reverse("bookings:api_boleto_retry", kwargs={"pk": self.boleto_alpha.pk})

        with patch("apps.common.utils.celery_utils.safe_delay") as mock_safe_delay:
            mock_safe_delay.return_value = True
            response = self.client.post(url, secure=True)

        self.assertIn(response.status_code, (200, 202))
        mock_safe_delay.assert_called_once()


class VentaDoubleInvoiceIDORTest(TestCase):
    """
    P0-003: Un usuario de la Agencia Beta NO puede facturar (double-invoice)
    una venta de la Agencia Alpha cambiando solo el pk de la URL.
    Esperado: 404, no 403, no 200.

    Nota: la vista realmente conectada a la URL `finance:api_venta_double_invoice`
    vive en apps/finance/views/invoice_views.py (NO en apps/bookings/views/boleto_views.py,
    que es una copia muerta/duplicada).
    """

    def setUp(self):
        """setUp."""
        patcher_delay = _silence_celery()
        self.mock_delay = patcher_delay.start()
        self.addCleanup(patcher_delay.stop)

        self.agencia_a = Agencia.objects.create(
            nombre="Agencia Alpha IDOR Fin", rif="J-3000003-3", activa=True
        )
        self.agencia_b = Agencia.objects.create(
            nombre="Agencia Beta IDOR Fin", rif="J-4000004-4", activa=True
        )
        self.moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )

        # Atacante (Agencia B)
        self.user_b = User.objects.create_user(username="user_beta_fin_idor", password="pw123")  # noqa: S106
        UsuarioAgencia.objects.create(
            usuario=self.user_b, agencia=self.agencia_b, rol="contador", activo=True
        )

        # Venta víctima (Agencia A). Replicamos el patrón de test_rbac.py /
        # test_bookings_legacy.py: patchear get_current_agency durante el create.
        with patch("core.models.base.get_current_agency", return_value=self.agencia_a):
            self.venta_alpha = Venta.objects.create(
                localizador="PNR-ALPHA-IDOR",
                moneda=self.moneda,
                subtotal=Decimal("150.00"),
            )

    def test_usuario_beta_no_puede_facturar_venta_de_alpha(self):
        """
        Atacante pertenece a Agencia B intenta double-invoice de venta de Agencia A.
        Debe recibir 404. Que NO se invoque InvoiceService (no facturación ilegítima).
        """
        self.client.force_login(self.user_b)

        url = reverse(
            "finance:api_venta_double_invoice",
            kwargs={"pk": self.venta_alpha.pk},
        )

        with patch(
            "apps.finance.services.invoice_service.InvoiceService.generate_double_invoice"
        ) as mock_gen:
            response = self.client.post(url, secure=True)

        self.assertEqual(
            response.status_code,
            404,
            "IDOR NO corregido: un usuario de otra agencia pudo facturar la venta ajena.",
        )
        mock_gen.assert_not_called()

    def test_usuario_alpha_si_puede_facturar_su_propia_venta(self):
        """Sanity: el propietario sí puede invocar el endpoint sin 404."""
        user_a = User.objects.create_user(username="user_alpha_fin_idor", password="pw123")  # noqa: S106
        UsuarioAgencia.objects.create(
            usuario=user_a, agencia=self.agencia_a, rol="contador", activo=True
        )
        self.client.force_login(user_a)

        url = reverse(
            "finance:api_venta_double_invoice",
            kwargs={"pk": self.venta_alpha.pk},
        )

        # Mockeamos el servicio para no depender de la infraestructura de facturación.
        # Lo importante es que el endpoint no devuelva 404: pasa el candado de tenant.
        from unittest.mock import MagicMock

        factura_mock = MagicMock(pk=9999)
        with patch(
            "apps.finance.services.invoice_service.InvoiceService.generate_double_invoice",
            return_value=(factura_mock, factura_mock),
        ):
            response = self.client.post(url, secure=True)

        self.assertEqual(response.status_code, 200)
