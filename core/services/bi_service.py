import logging
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from apps.bookings.models import Venta, ItemVenta
from apps.finance.models.tax_refund import TaxRefundOpportunity

logger = logging.getLogger(__name__)

class BusinessIntelligenceEngine:
    """
    MOTOR DE AGREGACIÓN BI:
    Provee métricas de alto rendimiento para el Dashboard del CEO.
    """
    
    @staticmethod
    def obtener_kpis_ceo(agencia):
        hoy = timezone.now()
        inicio_mes_actual = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Calcular el inicio del mes pasado (manejando el cambio de año)
        mes_pasado = inicio_mes_actual.month - 1 if inicio_mes_actual.month > 1 else 12
        anio_pasado = inicio_mes_actual.year if inicio_mes_actual.month > 1 else inicio_mes_actual.year - 1
        inicio_mes_pasado = inicio_mes_actual.replace(year=anio_pasado, month=mes_pasado)

        # 1. Ventas del Mes Actual
        ventas_actuales = Venta.objects.filter(agencia=agencia, fecha_venta__gte=inicio_mes_actual)
        total_ventas_actual = ventas_actuales.aggregate(Sum('total_venta'))['total_venta__sum'] or Decimal('0.00')
        boletos_emitidos = ItemVenta.objects.filter(venta__in=ventas_actuales).count()

        # 2. Utilidad Bruta Estimada (suma de las comisiones de la agencia en el mes)
        utilidad_actual = ItemVenta.objects.filter(venta__in=ventas_actuales).aggregate(Sum('comision_agencia_monto'))['comision_agencia_monto__sum'] or Decimal('0.00')

        # 3. Ventas del Mes Pasado (Para comparar crecimiento)
        ventas_pasadas = Venta.objects.filter(agencia=agencia, fecha_venta__gte=inicio_mes_pasado, fecha_venta__lt=inicio_mes_actual)
        total_ventas_pasado = ventas_pasadas.aggregate(Sum('total_venta'))['total_venta__sum'] or Decimal('0.00')

        # 4. Cálculo de Crecimiento (%)
        if total_ventas_pasado > 0:
            crecimiento = ((total_ventas_actual - total_ventas_pasado) / total_ventas_pasado) * 100
        else:
            crecimiento = 100.0 if total_ventas_actual > 0 else 0.0

        # 5. Dinero Sobre la Mesa (Tax Refund acumulado en estado Elegible)
        # Adaptado al nuevo modelo TaxRefundOpportunity
        tax_refund_elegible = TaxRefundOpportunity.objects.filter(agencia=agencia, estado='ELE').aggregate(Sum('monto_estimado'))['monto_estimado__sum'] or Decimal('0.00')

        return {
            'ventas_mes_actual': float(total_ventas_actual),
            'ventas_mes_pasado': float(total_ventas_pasado),
            'crecimiento_porcentaje': round(float(crecimiento), 1),
            'boletos_emitidos': boletos_emitidos,
            'utilidad_bruta': float(utilidad_actual),
            'tax_refund_disponible': float(tax_refund_elegible),
            'mes_actual_nombre': hoy.strftime('%B').capitalize()
        }

    @classmethod
    def get_monthly_sales_chart_data(cls, agencia):
        """
        Prepara los datos para el gráfico de barras de Chart.js.
        Últimos 6 meses.
        """
        data = []
        labels = []
        hoy = timezone.now()
        
        for i in range(5, -1, -1):
            mes = hoy.replace(day=1) - timedelta(days=i*30)
            inicio = mes.replace(day=1)
            fin = (inicio + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            total = Venta.objects.filter(
                agencia=agencia,
                fecha_venta__range=(inicio, fin)
            ).aggregate(s=Sum('total_venta'))['s'] or 0
            
            labels.append(inicio.strftime('%b'))
            data.append(float(total))
            
        return {'labels': labels, 'values': data}
