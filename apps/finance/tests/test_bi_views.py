"""Vistas (views) de la aplicación finance.
"""

from decimal import Decimal

import pytest
from django.urls import reverse

from apps.bookings.models.pagos import PagoVenta
from apps.bookings.models.venta import Venta
from core.middleware import agency_context
from core.models.agencia import UsuarioAgencia


@pytest.fixture
def no_ssl_redirect(settings):
    # no_ssl_redirect: No ssl redirect. Args: según implementación. Returns: según implementación.
    settings.SECURE_SSL_REDIRECT = False


@pytest.mark.django_db
@pytest.mark.usefixtures("no_ssl_redirect")
class TestBIDashboardView:
    """Vista para gestionar testbidashboard. Uso: instanciar según necesidad del dominio.
    """
    def test_dashboard_requires_login(self, client):
        """Verificar que la vista del Dashboard de BI requiere login."""
        url = reverse("finance:dashboard_bi")
        response = client.get(url, secure=True)
        # Debe redirigir al login
        assert response.status_code == 302
        assert "login" in response.url

    def test_dashboard_tenant_isolation(
        self, client, usuario_api, agencia_premium, agencia_estandar, moneda_usd
    ):
        """Regla SaaS: El dashboard de BI de una agencia solo debe listar sus ventas y no las de otra."""
        # 1. Asociar el usuario de pruebas a la Agencia Premium
        UsuarioAgencia.objects.create(
            usuario=usuario_api, agencia=agencia_premium, rol="admin", activo=True
        )

        # 2. Crear ventas en ambas agencias
        with agency_context(agencia_premium):
            venta_premium = Venta.objects.create(
                localizador="PREM99",
                moneda=moneda_usd,
                monto_neto_proveedor=Decimal("800.00"),
                monto_venta_cliente=Decimal("1000.00"),
                subtotal=Decimal("1000.00"),
                agencia=agencia_premium,
            )

        with agency_context(agencia_estandar):
            venta_estandar = Venta.objects.create(
                localizador="ESTD11",
                moneda=moneda_usd,
                monto_neto_proveedor=Decimal("400.00"),
                monto_venta_cliente=Decimal("500.00"),
                subtotal=Decimal("500.00"),
                agencia=agencia_estandar,
            )

        # 3. Loguearse y acceder al dashboard de la Agencia Premium
        client.force_login(usuario_api)

        # Para forzar la cookie del tenant/middleware o el estado activo
        session = client.session
        session["_agencia_activa_id"] = agencia_premium.pk
        session.save()

        # Mockear el middleware o depender del middleware de dominio/sesión
        url = reverse("finance:dashboard_bi")
        response = client.get(url, secure=True)

        assert response.status_code == 200
        ventas_visibles = response.context["ventas"]

        # Debe ver la de su propia agencia, pero NO la de la otra
        assert venta_premium in ventas_visibles
        assert venta_estandar not in ventas_visibles

    def test_dashboard_metrics_calculation(self, client, usuario_api, agencia_premium, moneda_usd):
        """Verifica que el cálculo agregado de métricas e IGTF sea preciso."""
        # 1. Asociar usuario
        UsuarioAgencia.objects.create(
            usuario=usuario_api, agencia=agencia_premium, rol="admin", activo=True
        )

        # 2. Crear venta y pagos
        with agency_context(agencia_premium):
            venta = Venta.objects.create(
                localizador="BI0012",
                moneda=moneda_usd,
                monto_neto_proveedor=Decimal("1000.00"),
                monto_venta_cliente=Decimal("1200.00"),
                subtotal=Decimal("1200.00"),
                porcentaje_comision_agente=Decimal("10.00"),
                agencia=agencia_premium,
            )

            # Pago en efectivo (Sujeto a IGTF 3%)
            PagoVenta.objects.create(
                venta=venta,
                monto=Decimal("500.00"),
                moneda=moneda_usd,
                metodo="EFE",
                confirmado=True,
                agencia=agencia_premium,
            )

            # Pago exento (Zelle)
            PagoVenta.objects.create(
                venta=venta,
                monto=Decimal("700.00"),
                moneda=moneda_usd,
                metodo="ZEL",
                confirmado=True,
                agencia=agencia_premium,
            )

        # 3. Acceder al dashboard
        client.force_login(usuario_api)
        url = reverse("finance:dashboard_bi")
        response = client.get(url, secure=True)

        assert response.status_code == 200
        metrics = response.context["metrics"]

        # Validar métricas
        # Total neto GDS = 1000
        assert metrics["total_neto_proveedor"] == Decimal("1000.00")
        # Total venta cliente = 1200
        assert metrics["total_venta_cliente"] == Decimal("1200.00")
        # Markup bruto = 200
        assert metrics["markup_bruto_total"] == Decimal("200.00")
        # IGTF = 500 * 3% = 15.00
        assert metrics["retenciones_igtf_total"] == Decimal("15.00")
        # Utilidad Neta Real = 200 - 15 = 185.00
        assert metrics["utilidad_neta_total"] == Decimal("185.00")
