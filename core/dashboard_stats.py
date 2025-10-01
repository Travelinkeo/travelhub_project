"""
Utilidades para calcular estadísticas del dashboard
"""
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from .models import Venta, ItemVenta, PagoVenta
from .models_catalogos import ProductoServicio


def get_dashboard_stats():
    """Obtiene estadísticas principales para el dashboard"""
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    hace_30_dias = hoy - timedelta(days=30)
    
    # Ventas del mes actual
    ventas_mes = Venta.objects.filter(fecha_venta__date__gte=inicio_mes)
    total_ventas_mes = ventas_mes.aggregate(
        total=Sum('total_venta'),
        count=Count('id_venta')
    )
    
    # Ventas últimos 30 días
    ventas_30d = Venta.objects.filter(fecha_venta__date__gte=hace_30_dias)
    total_ventas_30d = ventas_30d.aggregate(
        total=Sum('total_venta'),
        count=Count('id_venta')
    )
    
    # Ventas pendientes de pago
    ventas_pendientes = Venta.objects.filter(
        estado__in=['PEN', 'PAR']
    ).aggregate(
        total=Sum('saldo_pendiente'),
        count=Count('id_venta')
    )
    
    # Pagos recibidos este mes
    pagos_mes = PagoVenta.objects.filter(
        fecha_pago__date__gte=inicio_mes,
        confirmado=True
    ).aggregate(total=Sum('monto'))
    
    # Top productos por cantidad
    top_productos = ItemVenta.objects.filter(
        venta__fecha_venta__date__gte=hace_30_dias
    ).values(
        'producto_servicio__nombre',
        'producto_servicio__tipo_producto'
    ).annotate(
        cantidad_total=Sum('cantidad'),
        monto_total=Sum('total_item_venta')
    ).order_by('-cantidad_total')[:5]
    
    return {
        'ventas_mes': {
            'total': total_ventas_mes['total'] or Decimal('0'),
            'count': total_ventas_mes['count'] or 0
        },
        'ventas_30d': {
            'total': total_ventas_30d['total'] or Decimal('0'),
            'count': total_ventas_30d['count'] or 0
        },
        'pendientes_pago': {
            'total': ventas_pendientes['total'] or Decimal('0'),
            'count': ventas_pendientes['count'] or 0
        },
        'pagos_mes': {
            'total': pagos_mes['total'] or Decimal('0')
        },
        'top_productos': list(top_productos)
    }