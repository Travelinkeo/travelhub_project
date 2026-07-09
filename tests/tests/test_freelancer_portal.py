from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bookings.models import BoletoImportado, Venta
from apps.crm.models import ComisionFreelancer, FreelancerProfile
from apps.crm.services.freelancer_service import FreelancerService
from apps.crm.tasks import liquidar_comisiones_mensual_task
from core.models import Agencia

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestFreelancerPortal:
    """
    Suite de pruebas para el cálculo de comisiones, splits y liquidación de freelancers.
    """

    @pytest.fixture(autouse=True)
    def setup_data(self):
        # 1. Crear Agencia
        self.agencia = Agencia.objects.create(nombre="Freelancer Test Agency")

        # 2. Crear Usuario Freelancer y su Perfil
        self.user_freelancer = User.objects.create_user(
            username="freelancer1",
            email="free@test.com",
            password="password123",
            first_name="John",
            last_name="Freelancer",
        )
        self.perfil = FreelancerProfile.objects.create(
            usuario=self.user_freelancer,
            agencia=self.agencia,
            porcentaje_comision=Decimal("70.00"),  # Split 70%
            comision_fija_por_boleto=Decimal("15.00"),  # $15 fijo por boleto
            activo=True,
        )

    def test_commission_calculation_on_venta_save(self):
        """
        Verifica que al guardar una venta creada por el freelancer,
        se calcule la comisión combinada (porcentaje + fija) y se actualice el saldo.
        """
        # Crear la venta
        # markup_bruto = monto_venta_cliente - monto_neto_proveedor = 200 - 100 = 100
        venta = Venta.objects.create(
            agencia=self.agencia,
            localizador="FLX123",
            monto_venta_cliente=Decimal("200.00"),
            monto_neto_proveedor=Decimal("100.00"),
            creado_por=self.user_freelancer,
        )

        # Asociar un boleto para gatillar la comisión fija
        BoletoImportado.objects.create(
            agencia=self.agencia,
            venta_asociada=venta,
            numero_boleto="9990000000001",
            tarifa_base=Decimal("200.00"),
        )

        # Guardar la venta de nuevo para disparar el recálculo (incluyendo el boleto en el conteo)
        venta.save()

        # Verificar que se creó la comisión
        comision = ComisionFreelancer.objects.filter(venta=venta).first()
        assert comision is not None
        assert comision.freelancer == self.perfil
        assert comision.liquidada is False

        # Markup = 100. Split 70% = 70. 1 boleto * 15 fijo = 15. Total = 85.
        assert comision.monto_comision_ganada == Decimal("85.00")

        # Verificar saldo por cobrar
        self.perfil.refresh_from_db()
        assert self.perfil.saldo_por_cobrar == Decimal("85.00")
        assert self.perfil.total_historico_pagado == Decimal("0.00")

    def test_recalculate_balances_and_manual_liquidation(self):
        """
        Verifica que la recalculación y la liquidación de comisiones
        mueva los fondos de saldo_por_cobrar a total_historico_pagado.
        """
        venta = Venta.objects.create(
            agencia=self.agencia,
            localizador="FLX456",
            monto_venta_cliente=Decimal("100.00"),
            monto_neto_proveedor=Decimal("50.00"),
            creado_por=self.user_freelancer,
        )

        # Comisión esperada: Markup = 50. Split 70% = 35. 0 boletos = 0 fijo. Total = 35.
        venta.save()

        comision = ComisionFreelancer.objects.filter(venta=venta).first()
        assert comision is not None
        assert comision.monto_comision_ganada == Decimal("35.00")

        self.perfil.refresh_from_db()
        assert self.perfil.saldo_por_cobrar == Decimal("35.00")

        # Liquidar manualmente la comisión
        comision.liquidada = True
        comision.fecha_liquidacion = timezone.now()
        comision.save()

        # Forzar recalculo de balances
        FreelancerService.recalculate_balances(self.perfil)

        self.perfil.refresh_from_db()
        assert self.perfil.saldo_por_cobrar == Decimal("0.00")
        assert self.perfil.total_historico_pagado == Decimal("35.00")

    def test_liquidar_comisiones_mensual_task(self):
        """
        Verifica que la tarea Celery mensual de liquidación procese todas
        las comisiones no liquidadas de freelancers activos.
        """
        # Crear 2 ventas con comisiones
        venta1 = Venta.objects.create(
            agencia=self.agencia,
            localizador="FLX789",
            monto_venta_cliente=Decimal("100.00"),
            monto_neto_proveedor=Decimal("80.00"),
            creado_por=self.user_freelancer,
        )
        venta1.save()

        venta2 = Venta.objects.create(
            agencia=self.agencia,
            localizador="FLX012",
            monto_venta_cliente=Decimal("150.00"),
            monto_neto_proveedor=Decimal("100.00"),
            creado_por=self.user_freelancer,
        )
        venta2.save()

        # Comisiones generadas:
        # Venta 1: markup = 20 -> split 70% = 14.
        # Venta 2: markup = 50 -> split 70% = 35.
        # Saldo por cobrar total esperado: 49.00
        self.perfil.refresh_from_db()
        assert self.perfil.saldo_por_cobrar == Decimal("49.00")

        # Ejecutar la tarea de Celery
        result = liquidar_comisiones_mensual_task()
        assert "Liquidación completada exitosamente" in result

        # Las comisiones deberían estar marcadas como liquidadas
        comisiones = ComisionFreelancer.objects.filter(freelancer=self.perfil)
        assert comisiones.count() == 2
        for com in comisiones:
            assert com.liquidada is True
            assert com.fecha_liquidacion is not None

        # El saldo del perfil debe estar en histórico pagado
        self.perfil.refresh_from_db()
        assert self.perfil.saldo_por_cobrar == Decimal("0.00")
        assert self.perfil.total_historico_pagado == Decimal("49.00")
