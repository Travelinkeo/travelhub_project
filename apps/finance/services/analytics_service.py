from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
from apps.bookings.models import ItemVenta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class FinancialAnalyticsService:
    """
    Servicio para calcular métricas de rentabilidad en tiempo real.
    """

    @staticmethod
    def get_monthly_profitability():
        """
        Calcula ventas, costos y ganancias por mes.
        """
        # Agrupar por mes
        stats = ItemVenta.objects.annotate(
            month=TruncMonth('venta__fecha_venta')
        ).values('month').annotate(
            ingresos=Sum(F('precio_unitario_venta') * F('cantidad')),
            costos=Sum(
                (F('costo_neto_proveedor') or Decimal('0.00')) + 
                (F('fee_proveedor') or Decimal('0.00'))
            ),
        ).order_by('month')

        results = []
        for s in stats:
            ingresos = s['ingresos'] or Decimal('0')
            costos = s['costos'] or Decimal('0')
            margen = ingresos - costos
            results.append({
                'month': s['month'].strftime('%b %Y') if s['month'] else 'N/A',
                'ingresos': float(ingresos),
                'costos': float(costos),
                'margen': float(margen),
                'porcentaje': float((margen / ingresos * 100)) if ingresos > 0 else 0
            })
        
        return results

    @staticmethod
    def get_real_time_metrics():
        """
        Métricas clave para las tarjetas del dashboard.
        """
        total_data = ItemVenta.objects.aggregate(
            ventas=Sum(F('precio_unitario_venta') * F('cantidad')),
            costos=Sum(
                (F('costo_neto_proveedor') or Decimal('0.00')) + 
                (F('fee_proveedor') or Decimal('0.00'))
            )
        )
        
        ventas = total_data['ventas'] or Decimal('0')
        costos = total_data['costos'] or Decimal('0')
        margen = ventas - costos
        
        return {
            'ventas_totales': float(ventas),
            'costos_totales': float(costos),
            'margen_neto': float(margen),
            'porcentaje_margen': float((margen / ventas * 100)) if ventas > 0 else 0
        }

    @staticmethod
    def get_profit_by_category():
        """
        Margen por tipo de producto (Vuelos, Hoteles, etc.)
        """
        stats = ItemVenta.objects.values('producto_servicio__nombre').annotate(
            margen=Sum(
                (F('precio_unitario_venta') * F('cantidad')) - 
                ((F('costo_neto_proveedor') or Decimal('0.00')) + (F('fee_proveedor') or Decimal('0.00')))
            )
        ).order_by('-margen')
        
        return [{'name': s['producto_servicio__nombre'], 'value': float(s['margen'])} for s in stats if s['margen']]
