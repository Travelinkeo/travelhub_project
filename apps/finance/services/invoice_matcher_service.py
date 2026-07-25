"""Servicio de invoice matcher service para la aplicación finance.
"""

import logging
from decimal import Decimal

from apps.bookings.models.venta import ItemVenta
from apps.finance.models_stubs import FacturaProveedor

logger = logging.getLogger(__name__)


class InvoiceMatcherService:
    """
    Servicio de Dominio encargado de encontrar posibles 'matches'
    (conciliaciones) entre facturas de proveedores y ventas en el sistema.
    Abstrae la lógica pesada de la Vista (Fat View) y optimiza N+1.
    """

    @classmethod
    def get_potential_matches_for_invoice(cls, factura: FacturaProveedor) -> list[dict]:
        """
        Busca candidatos de ItemVenta que coincidan por monto o PNR.
        """
        agencia_id = factura.agencia_id
        monto = factura.monto_total
        moneda = factura.moneda

        if not monto:
            return []

        # Rango de búsqueda: monto +/- 5%
        tolerancia = monto * Decimal("0.05")

        # Optimizamos consultas trayendo los campos necesarios para comparar (Evitamos N+1 de los campos anidados)
        candidatos = ItemVenta.objects.filter(
            agencia_id=agencia_id, venta__moneda=moneda, estado_item__in=["PCO", "CNF", "UTI"]
        ).select_related("venta", "proveedor_servicio")

        posibles = []
        raw_data = str(factura.datos_json).upper()

        for c in candidatos:
            costo_erp = (c.costo_neto_proveedor or Decimal("0.00")) + (
                c.fee_proveedor or Decimal("0.00")
            )
            diff = abs(costo_erp - monto)

            # Match por PNR (si está en el JSON de la factura)
            pnr_match = False

            if c.codigo_reserva_proveedor and c.codigo_reserva_proveedor.upper() in raw_data:
                pnr_match = True
            elif c.venta.localizador and c.venta.localizador.upper() in raw_data:
                pnr_match = True

            if diff <= tolerancia or pnr_match:
                score = 0
                if diff <= Decimal("0.01"):
                    score += 50
                elif diff <= tolerancia:
                    score += 20

                if pnr_match:
                    score += 60

                posibles.append(
                    {"item": c, "score": score, "costo_total": costo_erp, "diferencia": diff}
                )

        # Ordenar por score
        posibles.sort(key=lambda x: x["score"], reverse=True)
        return posibles[:5]
