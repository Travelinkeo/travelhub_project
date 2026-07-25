"""Pruebas para bookings legacy en bookings.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils.module_loading import import_string

from apps.bookings.models import FeeVenta, ItemVenta, PagoVenta, ProductoServicio, Venta
from apps.common.models import Moneda
from core.models.agencia import Agencia


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class SeguridadSaaSTest(TestCase):
    """
    🛡️ BLINDAJE DE SEGURIDAD (Pruebas de Aislamiento Multi-Tenant)
    Valida que el AgenciaManager filtre correctamente los datos según el contexto.
    """

    def setUp(self):
        # Desactivar tareas de Celery reales durante el test
        patcher = patch("core.tasks.migrar_logos_agencia_task.delay")
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        # Crear Agencias de prueba
        self.agencia_a = Agencia.objects.create(
            nombre="Agencia Alpha", rif="J-11111111-1", activa=True
        )
        self.agencia_b = Agencia.objects.create(
            nombre="Agencia Beta", rif="J-22222222-2", activa=True
        )

        # Crear Moneda para evitar errores de Foreign Key si es requerida
        self.moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )

        # Crear Venta para Agencia Alpha
        # Forzamos el contexto de Agencia Alpha para la creación inicial
        with patch("core.models.base.get_current_agency", return_value=self.agencia_a):
            self.venta_alpha = Venta.objects.create(
                localizador="PNR-ALPHA-TEST",
                moneda=self.moneda,
                subtotal=Decimal("500.00"),
                impuestos=Decimal("80.00"),
            )

    def test_aislamiento_estricto_agencias(self):
        """
        Garantiza que la Agencia Beta no pueda ver la venta de Agencia Alpha
        aunque use Venta.objects.all().
        """
        # 1. Simular que el middleware detectó a la Agencia Beta
        with patch("core.models.base.get_current_agency", return_value=self.agencia_b):
            with patch("core.models.base.get_current_user", return_value=None):  # No es superuser
                # El manager 'AgenciaManager' debe filtrar automáticamente por la agencia en contexto
                ventas_visibles = Venta.objects.all()

                self.assertEqual(
                    ventas_visibles.count(),
                    0,
                    "🚨 CRÍTICO: Fuga de datos detectada. Una agencia puede ver registros de otra.",
                )

    def test_visibilidad_propia(self):
        """Validar que una agencia sí vea sus propios datos."""
        with patch("core.models.base.get_current_agency", return_value=self.agencia_a):
            ventas_visibles = Venta.objects.all()
            self.assertEqual(ventas_visibles.count(), 1)
            self.assertEqual(ventas_visibles.first().localizador, "PNR-ALPHA-TEST")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class CalculoFinancieroTest(TestCase):
    """
    📊 MOTOR FINANCIERO (Pruebas de Aritmética e Integridad)
    Garantiza que recalcular_finanzas() genere totales y saldos exactos.
    """

    def setUp(self):
        # Desactivar tareas de Celery reales durante el test
        patcher = patch("core.tasks.migrar_logos_agencia_task.delay")
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        self.agencia = Agencia.objects.create(
            nombre="Agencia Finanzas", rif="J-99999999-9", activa=True
        )
        self.moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )
        self.producto = ProductoServicio.objects.create(
            nombre="Vuelo Nacional", tipo_producto="AIR"
        )

        # Mockeamos el contexto para la creación
        with patch("core.models.base.get_current_agency", return_value=self.agencia):
            self.venta = Venta.objects.create(
                localizador="VTA-ARITMETICA",
                moneda=self.moneda,
                subtotal=Decimal("0.00"),
                impuestos=Decimal("15.00"),  # Impuesto manual de cabecera
            )

    def test_motor_recalculo_completo(self):
        """
        Valida el flujo:
        Items ($200) + Impuestos ($15) + Fees ($10) - Pagos ($50) = Saldo ($175)
        """
        with patch("core.models.base.get_current_agency", return_value=self.agencia):
            # 1. Agregar un Item ($200) + Impuesto ($15)
            ItemVenta.objects.create(
                venta=self.venta,
                producto_servicio=self.producto,
                cantidad=2,
                precio_unitario_venta=Decimal("100.00"),  # 2 * 100 = 200
                impuestos_item_venta=Decimal("7.50"),  # 2 * 7.50 = 15.00
            )

            # 2. Agregar un Fee de Gestión ($10)
            FeeVenta.objects.create(
                venta=self.venta, monto=Decimal("10.00"), moneda=self.moneda, tipo_fee="GST"
            )

            # 3. Agregar un Pago Parcial Confirmado ($50)
            PagoVenta.objects.create(
                venta=self.venta, monto=Decimal("50.00"), moneda=self.moneda, confirmado=True
            )

            # Disparar el motor de cálculo
            self.venta.recalcular_finanzas()
            self.venta.refresh_from_db()

            # --- ASSERTIONS ---
            # Subtotal debe ser la suma de items: 200.00
            self.assertEqual(self.venta.subtotal, Decimal("200.00"))

            # Total = 200 (subtotal) + 15 (impuestos manuales) + 10 (fees) = 225.00
            self.assertEqual(self.venta.total_venta, Decimal("225.00"))

            # Pagado = 50.00
            self.assertEqual(self.venta.monto_pagado, Decimal("50.00"))

            # Saldo = 225 - 50 = 175.00
            self.assertEqual(self.venta.saldo_pendiente, Decimal("175.00"))

            # El estado debe ser 'Pagada Parcialmente' (PAR)
            self.assertEqual(self.venta.estado, Venta.EstadoVenta.PAGADA_PARCIAL)

    def test_pago_total_cambia_estado(self):
        """Valida que al cubrir el saldo, el estado cambie a PAGADA_TOTAL automáticamente."""
        with patch("core.models.base.get_current_agency", return_value=self.agencia):
            # Agregar Item por el total base ($15)
            ItemVenta.objects.create(
                venta=self.venta,
                producto_servicio=self.producto,
                cantidad=1,
                precio_unitario_venta=Decimal("15.00"),
                impuestos_item_venta=Decimal("0.00"),
            )

            # Crear un pago por el total (Total base 15)
            PagoVenta.objects.create(
                venta=self.venta, monto=Decimal("15.00"), moneda=self.moneda, confirmado=True
            )

            self.venta.recalcular_finanzas()
            self.venta.refresh_from_db()

            self.assertEqual(self.venta.saldo_pendiente, Decimal("0.00"))
            self.assertEqual(self.venta.estado, Venta.EstadoVenta.PAGADA_TOTAL)


class BIContableTest(TestCase):
    """
    📊 BUSINESS INTELLIGENCE & ANALYTICS (Pruebas del Módulo 2)
    Garantiza los cálculos correctos de margen y el funcionamiento del detector de fuga.
    """

    def setUp(self):
        # Desactivar tareas de Celery reales durante el test
        patcher = patch("core.tasks.migrar_logos_agencia_task.delay")
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        self.agencia = Agencia.objects.create(nombre="Agencia BI", rif="J-88888888-8", activa=True)
        self.moneda, _ = Moneda.objects.get_or_create(
            codigo_iso="USD", defaults={"nombre": "Dólar", "simbolo": "$"}
        )

    def test_calculos_margen_e_igtf(self):
        # test_calculos_margen_e_igtf: Test calculos margen e igtf. Args: según implementación. Returns: según implementación.
        with patch("core.models.base.get_current_agency", return_value=self.agencia):
            # Crear venta con campos BI de prueba
            venta = Venta.objects.create(
                localizador="VTA-BI-MARG",
                moneda=self.moneda,
                monto_neto_proveedor=Decimal("1000.00"),
                monto_venta_cliente=Decimal("1200.00"),
                subtotal=Decimal("1200.00"),
            )

            # Registrar pagos: uno en efectivo (sujeto a IGTF)
            PagoVenta.objects.create(
                venta=venta,
                monto=Decimal("500.00"),
                moneda=self.moneda,
                metodo="EFE",
                confirmado=True,
            )
            # Otro pago exento (Zelle)
            PagoVenta.objects.create(
                venta=venta,
                monto=Decimal("700.00"),
                moneda=self.moneda,
                metodo="ZEL",
                confirmado=True,
            )

            # Verificar propiedades de la Venta
            # 1. Markup Bruto = 1200 - 1000 = 200.00
            self.assertEqual(venta.markup_bruto, Decimal("200.00"))

            # 2. Retenciones estimadas IGTF = 500 * 3% = 15.00
            self.assertEqual(venta.retenciones_estimadas_igtf, Decimal("15.00"))

            # 3. Utilidad neta real = 200 - 15 = 185.00
            self.assertEqual(venta.utilidad_neta_real, Decimal("185.00"))

    @patch("apps.finance.tasks.enviar_alerta_telegram")
    def test_auditar_fuga_ingresos_task(self, mock_enviar):
        # test_auditar_fuga_ingresos_task: Test auditar fuga ingresos task. Args: según implementación. Returns: según implementación.
        with patch("core.models.base.get_current_agency", return_value=self.agencia):
            # Caso con fuga (monto_venta_cliente = 1500, pagado = 1000)
            venta_fuga = Venta.objects.create(
                localizador="VTA-FUGA-Y",
                moneda=self.moneda,
                monto_neto_proveedor=Decimal("800.00"),
                monto_venta_cliente=Decimal("1500.00"),
                monto_pagado=Decimal("1000.00"),
                subtotal=Decimal("1500.00"),
            )
            PagoVenta.objects.create(
                venta=venta_fuga,
                monto=Decimal("1000.00"),
                moneda=self.moneda,
                metodo="ZEL",
                confirmado=True,
            )

            # Caso sin fuga (monto_venta_cliente = 500, pagado = 500)
            venta_ok = Venta.objects.create(
                localizador="VTA-OK-S",
                moneda=self.moneda,
                monto_neto_proveedor=Decimal("400.00"),
                monto_venta_cliente=Decimal("500.00"),
                monto_pagado=Decimal("500.00"),
                subtotal=Decimal("500.00"),
            )
            PagoVenta.objects.create(
                venta=venta_ok,
                monto=Decimal("500.00"),
                moneda=self.moneda,
                metodo="ZEL",
                confirmado=True,
            )

        # Ejecutar la tarea de Celery

        auditar_fuga_ingresos_task = import_string("apps.finance.tasks.auditar_fuga_ingresos_task")
        resultado = auditar_fuga_ingresos_task()

        # Debe detectar brechas
        self.assertIn("Brechas detectadas: 1", resultado)
        self.assertTrue(mock_enviar.called)
