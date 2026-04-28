"""
Utilidades para calcular estadísticas del dashboard
"""
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum, Count, Q
from django.utils import timezone
from apps.bookings.models import Venta, ItemVenta, PagoVenta
from core.models_catalogos import ProductoServicio


def get_dashboard_stats(agencia):
    """
    Obtiene estadísticas principales para el dashboard, filtradas por agencia (Multi-tenant).
    """
    if not agencia:
        return {}

    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)
    hace_30_dias = hoy - timedelta(days=30)
    inicio_ano = hoy.replace(month=1, day=1)
    
    # Base Querysets blindados por agencia
    ventas_qs = Venta.objects.filter(agencia=agencia)
    pagos_qs = PagoVenta.objects.filter(agencia=agencia)
    items_qs = ItemVenta.objects.filter(agencia=agencia)

    # Ventas del mes actual
    ventas_mes = ventas_qs.filter(fecha_venta__date__gte=inicio_mes)
    total_ventas_mes = ventas_mes.aggregate(
        total=Sum('total_venta'),
        count=Count('id_venta')
    )
    
    # Ventas del año
    ventas_ano = ventas_qs.filter(fecha_venta__date__gte=inicio_ano)
    total_ventas_ano = ventas_ano.aggregate(
        total=Sum('total_venta'),
        count=Count('id_venta')
    )
    
    # Ventas últimos 30 días
    ventas_30d = ventas_qs.filter(fecha_venta__date__gte=hace_30_dias)
    total_ventas_30d = ventas_30d.aggregate(
        total=Sum('total_venta'),
        count=Count('id_venta')
    )
    
    # Métrica de Automatización (Workflow Mágico)
    ventas_auto = ventas_mes.filter(canal_origen='IMPORTACION').aggregate(
        total=Sum('total_venta'),
        count=Count('id_venta')
    )
    ventas_manual = ventas_mes.filter(canal_origen='MANUAL').count()

    # Ventas pendientes de pago
    ventas_pendientes = ventas_qs.filter(
        estado__in=['PEN', 'PAR']
    ).aggregate(
        total=Sum('saldo_pendiente'),
        count=Count('id_venta')
    )
    
    # Pagos recibidos este mes
    pagos_mes = pagos_qs.filter(
        fecha_pago__date__gte=inicio_mes,
        confirmado=True
    ).aggregate(total=Sum('monto'))
    
    # Top productos por cantidad
    top_productos = items_qs.filter(
        venta__fecha_venta__date__gte=hace_30_dias
    ).values(
        'producto_servicio__nombre',
        'producto_servicio__tipo_producto'
    ).annotate(
        cantidad_total=Sum('cantidad'),
        monto_total=Sum('total_item_venta')
    ).order_by('-monto_total')[:5]
    
    # Tendencia últimos 7 días
    tendencia = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        ventas_dia = ventas_qs.filter(
            fecha_venta__date=dia
        ).aggregate(
            total=Sum('total_venta'),
            count=Count('id_venta')
        )
        tendencia.append({
            'fecha': dia.isoformat(),
            'total': float(ventas_dia['total'] or 0),
            'count': ventas_dia['count'] or 0
        })
    
    # Margen promedio (Nivel 4 Profitability)
    items_con_margen = items_qs.filter(
        venta__fecha_venta__date__gte=inicio_mes,
        costo_neto_proveedor__isnull=False
    ).aggregate(
        total_venta=Sum('total_item_venta'),
        total_costo=Sum('costo_neto_proveedor'),
        count=Count('id_item_venta')
    )
    
    ganancia_total = (items_con_margen['total_venta'] or 0) - (items_con_margen['total_costo'] or 0)
    margen_promedio = (ganancia_total / items_con_margen['count']) if items_con_margen['count'] and items_con_margen['count'] > 0 else Decimal('0')
    
    return {
        'ventas_mes': {
            'total': float(total_ventas_mes['total'] or 0),
            'count': total_ventas_mes['count'] or 0
        },
        'ventas_ano': {
            'total': float(total_ventas_ano['total'] or 0),
            'count': total_ventas_ano['count'] or 0
        },
        'automatización': {
            'count_auto': ventas_auto['count'] or 0,
            'total_auto': float(ventas_auto['total'] or 0),
            'count_manual': ventas_manual
        },
        'ventas_30d': {
            'total': float(total_ventas_30d['total'] or 0),
            'count': total_ventas_30d['count'] or 0
        },
        'pendientes_pago': {
            'total': float(ventas_pendientes['total'] or 0),
            'count': ventas_pendientes['count'] or 0
        },
        'pagos_mes': {
            'total': float(pagos_mes['total'] or 0)
        },
        'margen_promedio': float(margen_promedio),
        'top_productos': list(top_productos),
        'tendencia_7dias': tendencia,
        'agencia_nombre': agencia.nombre
    }