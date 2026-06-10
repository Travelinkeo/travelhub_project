from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bookings.models import Venta
from apps.finance.models.recaudacion import CanalRecaudacion, Pago
from core.middleware import agency_context


@pytest.mark.django_db
class TestEngineRecaudacionFiscal:
    def test_aislamiento_multitenant_recaudacion(
        self, agencia_premium, agencia_estandar, moneda_usd
    ):
        """Regla SaaS: Un canal creado en la Agencia A no debe ser accesible por la Agencia B."""
        with agency_context(agencia_premium):
            canal_a = CanalRecaudacion.objects.create(
                nombre="Caja Fuerte Premium",
                tipo=CanalRecaudacion.TipoCanal.EFECTIVO,
                moneda=moneda_usd,
                agencia=agencia_premium,
            )

        # Validamos que la Agencia B no vea el canal a través de la consulta estándar
        with agency_context(agencia_estandar):
            canales_agencia_b = CanalRecaudacion.objects.all()
            assert canal_a not in canales_agencia_b

    def test_calculo_exitoso_igtf_divisas_cash(self, agencia_premium, moneda_usd):
        """Regla SENIAT: Si la agencia es Contribuyente Especial y el pago es USD Cash, aplica IGTF (3%)."""
        with agency_context(agencia_premium):
            canal_efectivo = CanalRecaudacion.objects.create(
                nombre="Caja USD Físico",
                tipo=CanalRecaudacion.TipoCanal.EFECTIVO,
                moneda=moneda_usd,
                agencia=agencia_premium,
            )

            venta = Venta.objects.create(
                localizador="AMAD12",
                agencia=agencia_premium,
                subtotal=Decimal("1000.00"),
                fecha_venta=timezone.now(),
            )

            pago = Pago.objects.create(
                venta=venta,
                canal_recaudacion=canal_efectivo,
                monto=Decimal("500.00"),
                moneda=moneda_usd,
                tasa_cambio=Decimal("36.50"),
                confirmado=True,
                agencia=agencia_premium,
            )

            assert pago.igtf_aplicado is True
            # 500 * 0.03 = 15.00
            assert pago.igtf_monto == Decimal("15.00")

    def test_exencion_igtf_en_consolidadores(self, agencia_premium, moneda_usd):
        """Regla de Negocio: Los pagos triangulados a cuentas de Consolidadores no pagan IGTF local."""
        with agency_context(agencia_premium):
            canal_consolidador = CanalRecaudacion.objects.create(
                nombre="Cuenta Puente Miami",
                tipo=CanalRecaudacion.TipoCanal.CONSOLIDADOR,
                moneda=moneda_usd,
                agencia=agencia_premium,
            )

            venta = Venta.objects.create(
                localizador="SABR99",
                agencia=agencia_premium,
                subtotal=Decimal("1000.00"),
                fecha_venta=timezone.now(),
            )

            pago = Pago.objects.create(
                venta=venta,
                canal_recaudacion=canal_consolidador,
                monto=Decimal("400.00"),
                moneda=moneda_usd,
                tasa_cambio=Decimal("36.50"),
                confirmado=True,
                agencia=agencia_premium,
            )

            assert pago.igtf_aplicado is False
            assert pago.igtf_monto == Decimal("0.00")
