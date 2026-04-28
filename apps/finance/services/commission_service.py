import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from apps.bookings.models import Venta
from apps.finance.models.commissions import ReglaComision, ComisionVenta

logger = logging.getLogger(__name__)

class CommissionService:
    @classmethod
    @transaction.atomic
    def calcular_comision_venta(cls, venta_id: int) -> bool:
        """
        MOTOR DE CÁLCULO DE COMISIONES IA-DRIVEN:
        Calcula la ganancia del agente basada en su tipo de regla y la 
        rentabilidad real de la venta.
        """
        try:
            # 1. Recuperar la Venta y sus items
            venta = Venta.objects.prefetch_related('items_venta').get(pk=venta_id)
            agente = venta.creado_por
           
            if not agente:
                logger.warning(f"Venta {venta_id} no tiene agente asignado. No se calcula comisión.")
                return False

            # 2. Localizar Regla de Comisión Activa para el Agente
            regla = ReglaComision.objects.filter(
                agencia=venta.agencia, 
                agente=agente, 
                activo=True
            ).first()

            if not regla:
                logger.warning(f"Agente {agente.username} no tiene una Regla de Comisión configurada.")
                return False

            # 3. Calcular Rentabilidad (Cuerpo del beneficio)
            # Rentabilidad = Ingresos Totales - Costos Netos del Proveedor
            total_venta = Decimal(str(venta.total_venta or 0))
            costo_proveedor = sum(
                Decimal(str(i.costo_neto_proveedor or 0)) * i.cantidad 
                for i in venta.items_venta.all()
            )
            rentabilidad = total_venta - costo_proveedor

            monto_comision = Decimal('0.00')
            base_calculo = Decimal('0.00')

            # 4. Lógica de Motor según el Tipo de Regla
            if regla.tipo_calculo == ReglaComision.TipoCalculo.PORCENTAJE_UTILIDAD:
                # Comision based on profit (ej: 50% of the Markup)
                base_calculo = rentabilidad
                # Evitar comisiones negativas si la venta cerró a pérdida
                if base_calculo > 0:
                    monto_comision = (base_calculo * (regla.valor / Decimal('100'))).quantize(Decimal('0.01'))
            
            elif regla.tipo_calculo == ReglaComision.TipoCalculo.PORCENTAJE_VENTA:
                # Comision based on Gros Volume (ej: 1% of total invoice)
                base_calculo = total_venta
                monto_comision = (base_calculo * (regla.valor / Decimal('100'))).quantize(Decimal('0.01'))

            elif regla.tipo_calculo == ReglaComision.TipoCalculo.MONTO_FIJO:
                # Comision based on Item Count (ej: $10 per booking)
                base_calculo = Decimal(str(venta.items_venta.count()))
                monto_comision = (regla.valor * base_calculo).quantize(Decimal('0.01'))

            # 5. Persistir el registro de comisión
            comision, created = ComisionVenta.objects.update_or_create(
                venta=venta,
                agente=agente,
                defaults={
                    'regla_aplicada': regla,
                    'monto_base_calculo': base_calculo,
                    'monto_comision': monto_comision,
                    'estado': ComisionVenta.EstadoComision.PENDIENTE
                }
            )

            logger.info(f"✅ Comisión de ${monto_comision} calculada para Agente {agente.username} (Venta {venta.localizador})")
            return True

        except Venta.DoesNotExist:
            logger.error(f"Venta ID {venta_id} no encontrada para cálculo de comisión.")
            return False
        except Exception as e:
            logger.exception(f"Falla crítica en el servicio de comisiones: {e}")
            return False
