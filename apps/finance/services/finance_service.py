"""Servicio de finance service para la aplicación finance.
"""

import logging
from decimal import Decimal

from django.db.models import Sum

from apps.bookings.models.venta import Venta

logger = logging.getLogger(__name__)


class FinanceService:
    """Servicio para finance. Uso: instanciar según necesidad del dominio.
    """
    @staticmethod
    def recalculate_sale_finances(venta_id):
        """
        Calcula y actualiza los totales de una venta basándose en sus items, fees y pagos.
        Esta lógica se extrae del modelo para evitar efectos secundarios en el .save()
        """
        try:
            venta = Venta.objects.get(pk=venta_id)

            # 1. Sumar items
            subtotal_items = Decimal("0.00")
            impuestos_items = Decimal("0.00")

            items = venta.items_venta.all()
            for item in items:
                subtotal_items += item.subtotal_item_venta
                impuestos_items += item.impuestos_item_venta * item.cantidad

            # 2. Sumar fees
            fees_total = venta.fees_venta.aggregate(s=Sum("monto"))["s"] or Decimal("0.00")

            # 3. Sumar pagos confirmados
            pagos_confirmados = venta.pagos_venta.filter(confirmado=True).aggregate(s=Sum("monto"))[
                "s"
            ] or Decimal("0.00")

            # 4. Actualizar campos
            venta.subtotal = subtotal_items
            venta.impuestos = impuestos_items
            venta.total_venta = subtotal_items + impuestos_items + fees_total
            venta.monto_pagado = pagos_confirmados
            venta.saldo_pendiente = venta.total_venta - venta.monto_pagado

            # 5. Determinar estado según saldo
            estado_original = venta.estado
            # Solo actualizamos el estado si es uno de los estados financieros base
            estados_financieros_base = {"PEN", "PAR", "PAG"}  # Códigos de estado

            if venta.estado in estados_financieros_base and venta.total_venta > 0:
                if venta.saldo_pendiente <= 0:
                    venta.estado = "PAG"  # Pagada Total
                elif 0 < venta.saldo_pendiente < venta.total_venta:
                    venta.estado = "PAR"  # Pagada Parcial
                else:
                    venta.estado = "PEN"  # Pendiente de Pago

            # 6. Guardado atómico de campos financieros
            campos_update = [
                "subtotal",
                "impuestos",
                "total_venta",
                "monto_pagado",
                "saldo_pendiente",
            ]
            if venta.estado != estado_original:
                campos_update.append("estado")

            venta.save(update_fields=campos_update)

            # Sincronizar factura si existe (excluyendo pagadas y anuladas)
            # stub

            # 7. Evaluación de puntos (Si aplica)
            if hasattr(venta, "_evaluar_otorgar_puntos"):
                venta._evaluar_otorgar_puntos(contexto="finance_service")

            return True
        except Venta.DoesNotExist:
            logger.error(f"Venta {venta_id} no encontrada para recalcular.")
            return False
        except Exception as e:
            logger.exception(f"Error recalculando finanzas de venta {venta_id}: {e}")
            return False
