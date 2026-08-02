# Archivo: apps/communications/services/booking_queries_service.py

from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


class BookingQueriesService:
    """Consulta datos de bookings (boletos importados y ventas) para otros dominios.

    Encapsula el acceso a apps.bookings desde comunicaciones, respetando la
    arquitectura por capas del Manifiesto (communications -> bookings es legal).
    """

    @classmethod
    def buscar_boleto_por_pnr(cls, pnr: str, agencia_id: int | None = None):
        """Retorna el BoletoImportado que coincide con el localizador (PNR).

        Args:
            pnr: Localizador a buscar (case-insensitive).
            agencia_id: Si se provee, restringe la búsqueda a esa agencia.
        Returns:
            BoletoImportado | None
        """
        from apps.bookings.models.importacion import BoletoImportado

        qs = BoletoImportado.objects.filter(localizador__iexact=pnr)
        if agencia_id:
            qs = qs.filter(agencia_id=agencia_id)
        return qs.first()

    @classmethod
    def resumen_ventas_del_dia(cls, dia: date | None = None, agencia_id: int | None = None) -> dict:
        """Resumen express de ventas emitidas en una fecha.

        Args:
            dia: Fecha a consultar (default: hoy).
            agencia_id: Si se provee, restringe a esa agencia.
        Returns:
            dict con 'total' (count) y 'monto_total' (suma de montos).
        """
        from apps.bookings.models.venta import Venta

        if dia is None:
            from django.utils import timezone

            dia = timezone.now().date()

        qs = Venta.objects.filter(fecha_venta__date=dia)
        if agencia_id:
            qs = qs.filter(agencia_id=agencia_id)

        monto_total = sum(v.monto_total or 0 for v in qs)
        return {"total": qs.count(), "monto_total": monto_total}
