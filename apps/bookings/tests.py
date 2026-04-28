from django.test import TestCase, override_settings
from unittest.mock import patch
from decimal import Decimal
from django.utils import timezone

# Modelos Reales
from core.models import Agencia
from apps.bookings.models import Venta, ItemVenta, FeeVenta, PagoVenta
from core.models_catalogos import Moneda, ProductoServicio

@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class SeguridadSaaSTest(TestCase):
    """
    🛡️ BLINDAJE DE SEGURIDAD (Pruebas de Aislamiento Multi-Tenant)
    Valida que el AgenciaManager filtre correctamente los datos según el contexto.
    """
    def setUp(self):
        # Desactivar tareas de Celery reales durante el test
        patcher = patch('core.tasks.migrar_logos_agencia_task.delay')
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        # Crear Agencias de prueba
        self.agencia_a = Agencia.objects.create(nombre="Agencia Alpha", rif="J-11111111-1", activa=True)
        self.agencia_b = Agencia.objects.create(nombre="Agencia Beta", rif="J-22222222-2", activa=True)
        
        # Crear Moneda para evitar errores de Foreign Key si es requerida
        self.moneda = Moneda.objects.create(nombre="Dólar", codigo_iso="USD", simbolo="$")
        
        # Crear Venta para Agencia Alpha
        # Forzamos el contexto de Agencia Alpha para la creación inicial
        with patch('core.models.base.get_current_agency', return_value=self.agencia_a):
            self.venta_alpha = Venta.objects.create(
                localizador="PNR-ALPHA-TEST",
                moneda=self.moneda,
                subtotal=Decimal('500.00'),
                impuestos=Decimal('80.00')
            )

    def test_aislamiento_estricto_agencias(self):
        """
        Garantiza que la Agencia Beta no pueda ver la venta de Agencia Alpha
        aunque use Venta.objects.all().
        """
        # 1. Simular que el middleware detectó a la Agencia Beta
        with patch('core.models.base.get_current_agency', return_value=self.agencia_b):
            with patch('core.models.base.get_current_user', return_value=None): # No es superuser
                
                # El manager 'AgenciaManager' debe filtrar automáticamente por la agencia en contexto
                ventas_visibles = Venta.objects.all()
                
                self.assertEqual(
                    ventas_visibles.count(), 0, 
                    "🚨 CRÍTICO: Fuga de datos detectada. Una agencia puede ver registros de otra."
                )

    def test_visibilidad_propia(self):
        """Validar que una agencia sí vea sus propios datos."""
        with patch('core.models.base.get_current_agency', return_value=self.agencia_a):
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
        patcher = patch('core.tasks.migrar_logos_agencia_task.delay')
        self.mock_delay = patcher.start()
        self.addCleanup(patcher.stop)

        self.agencia = Agencia.objects.create(nombre="Agencia Finanzas", rif="J-99999999-9", activa=True)
        self.moneda = Moneda.objects.create(nombre="Dólar", codigo_iso="USD", simbolo="$")
        self.producto = ProductoServicio.objects.create(nombre="Vuelo Nacional", tipo_producto='AIR')
        
        # Mockeamos el contexto para la creación
        with patch('core.models.base.get_current_agency', return_value=self.agencia):
            self.venta = Venta.objects.create(
                localizador="VTA-ARITMETICA",
                moneda=self.moneda,
                subtotal=Decimal('0.00'),
                impuestos=Decimal('15.00') # Impuesto manual de cabecera
            )

    def test_motor_recalculo_completo(self):
        """
        Valida el flujo: 
        Items ($200) + Impuestos ($15) + Fees ($10) - Pagos ($50) = Saldo ($175)
        """
        with patch('core.models.base.get_current_agency', return_value=self.agencia):
            
            # 1. Agregar un Item ($200)
            ItemVenta.objects.create(
                venta=self.venta,
                producto_servicio=self.producto,
                cantidad=2,
                precio_unitario_venta=Decimal('100.00'), # 2 * 100 = 200
                impuestos_item_venta=Decimal('0.00')
            )
            
            # 2. Agregar un Fee de Gestión ($10)
            FeeVenta.objects.create(
                venta=self.venta,
                monto=Decimal('10.00'),
                moneda=self.moneda,
                tipo_fee='GST'
            )
            
            # 3. Agregar un Pago Parcial Confirmado ($50)
            PagoVenta.objects.create(
                venta=self.venta,
                monto=Decimal('50.00'),
                moneda=self.moneda,
                confirmado=True
            )
            
            # Disparar el motor de cálculo
            self.venta.recalcular_finanzas()
            
            # --- ASSERTIONS ---
            # Subtotal debe ser la suma de items: 200.00
            self.assertEqual(self.venta.subtotal, Decimal('200.00'))
            
            # Total = 200 (subtotal) + 15 (impuestos manuales) + 10 (fees) = 225.00
            self.assertEqual(self.venta.total_venta, Decimal('225.00'))
            
            # Pagado = 50.00
            self.assertEqual(self.venta.monto_pagado, Decimal('50.00'))
            
            # Saldo = 225 - 50 = 175.00
            self.assertEqual(self.venta.saldo_pendiente, Decimal('175.00'))
            
            # El estado debe ser 'Pagada Parcialmente' (PAR)
            self.assertEqual(self.venta.estado, Venta.EstadoVenta.PAGADA_PARCIAL)

    def test_pago_total_cambia_estado(self):
        """Valida que al cubrir el saldo, el estado cambie a PAGADA_TOTAL automáticamente."""
        with patch('core.models.base.get_current_agency', return_value=self.agencia):
            
            # Crear un pago por el total (Total base 15 + fee 0 + item 0)
            PagoVenta.objects.create(
                venta=self.venta,
                monto=Decimal('15.00'),
                moneda=self.moneda,
                confirmado=True
            )
            
            self.venta.recalcular_finanzas()
            
            self.assertEqual(self.venta.saldo_pendiente, Decimal('0.00'))
            self.assertEqual(self.venta.estado, Venta.EstadoVenta.PAGADA_TOTAL)

