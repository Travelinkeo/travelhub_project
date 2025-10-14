# core/views/dashboard_views.py
from datetime import timedelta
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Venta, Factura, LiquidacionProveedor, BoletoImportado
from core.throttling import DashboardRateThrottle
from core.cache import cache_api_response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([DashboardRateThrottle])
@cache_api_response(timeout=300, key_prefix='dashboard')
def dashboard_metricas(request):
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    ventas_qs = Venta.objects.all()
    if fecha_desde:
        ventas_qs = ventas_qs.filter(fecha_venta__gte=fecha_desde)
    if fecha_hasta:
        ventas_qs = ventas_qs.filter(fecha_venta__lte=fecha_hasta)
    
    total_ventas = ventas_qs.aggregate(
        count=Count('id_venta'),
        total=Sum('total_venta'),
        saldo_pendiente=Sum('saldo_pendiente'),
        margen=Sum('margen_estimado'),
        co2=Sum('co2_estimado_kg')
    )
    
    ventas_por_estado = list(ventas_qs.values('estado').annotate(
        count=Count('id_venta'),
        total=Sum('total_venta')
    ).order_by('-count'))
    
    top_clientes = list(ventas_qs.exclude(cliente__isnull=True).values(
        'cliente__id_cliente',
        'cliente__nombres',
        'cliente__apellidos',
        'cliente__nombre_empresa'
    ).annotate(
        total_compras=Sum('total_venta'),
        num_ventas=Count('id_venta')
    ).order_by('-total_compras')[:5])
    
    ventas_por_tipo = list(ventas_qs.values('tipo_venta').annotate(
        count=Count('id_venta'),
        total=Sum('total_venta')
    ))
    
    ventas_por_canal = list(ventas_qs.values('canal_origen').annotate(
        count=Count('id_venta'),
        total=Sum('total_venta')
    ))
    
    liquidaciones_pendientes = LiquidacionProveedor.objects.filter(
        estado='PEN'
    ).aggregate(
        count=Count('id_liquidacion'),
        total=Sum('monto_total')
    )
    
    facturas_pendientes = Factura.objects.filter(
        estado__in=['EMI', 'PAR']
    ).aggregate(
        count=Count('id_factura'),
        total=Sum('saldo_pendiente')
    )
    
    hoy = timezone.now().date()
    hace_7_dias = hoy - timedelta(days=7)
    tendencia_semanal = []
    for i in range(7):
        dia = hace_7_dias + timedelta(days=i)
        ventas_dia = Venta.objects.filter(fecha_venta__date=dia).aggregate(
            total=Sum('total_venta'),
            count=Count('id_venta')
        )
        tendencia_semanal.append({
            'fecha': dia.isoformat(),
            'total': float(ventas_dia['total'] or 0),
            'count': ventas_dia['count'] or 0
        })
    
    return Response({
        'resumen': {
            'total_ventas': total_ventas['count'] or 0,
            'monto_total': float(total_ventas['total'] or 0),
            'saldo_pendiente': float(total_ventas['saldo_pendiente'] or 0),
            'margen_estimado': float(total_ventas['margen'] or 0),
            'co2_estimado_kg': float(total_ventas['co2'] or 0),
        },
        'ventas_por_estado': ventas_por_estado,
        'ventas_por_tipo': ventas_por_tipo,
        'ventas_por_canal': ventas_por_canal,
        'top_clientes': top_clientes,
        'liquidaciones_pendientes': {
            'count': liquidaciones_pendientes['count'] or 0,
            'total': float(liquidaciones_pendientes['total'] or 0)
        },
        'facturas_pendientes': {
            'count': facturas_pendientes['count'] or 0,
            'total': float(facturas_pendientes['total'] or 0)
        },
        'tendencia_semanal': tendencia_semanal
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_alertas(request):
    ventas_sin_cliente = Venta.objects.filter(cliente__isnull=True).count()
    
    hace_7_dias = timezone.now() - timedelta(days=7)
    ventas_mora = Venta.objects.filter(
        saldo_pendiente__gt=0,
        fecha_venta__lt=hace_7_dias
    ).count()
    
    boletos_sin_venta = BoletoImportado.objects.filter(
        estado_parseo='COM',
        venta_asociada__isnull=True
    ).count()
    
    hace_30_dias = timezone.now() - timedelta(days=30)
    liquidaciones_vencidas = LiquidacionProveedor.objects.filter(
        estado='PEN',
        fecha_emision__lt=hace_30_dias
    ).count()
    
    return Response({
        'alertas': [
            {
                'tipo': 'ventas_sin_cliente',
                'count': ventas_sin_cliente,
                'mensaje': f'{ventas_sin_cliente} venta(s) sin cliente asignado',
                'severidad': 'warning' if ventas_sin_cliente > 0 else 'info'
            },
            {
                'tipo': 'ventas_mora',
                'count': ventas_mora,
                'mensaje': f'{ventas_mora} venta(s) con saldo pendiente > 7 días',
                'severidad': 'error' if ventas_mora > 0 else 'info'
            },
            {
                'tipo': 'boletos_sin_venta',
                'count': boletos_sin_venta,
                'mensaje': f'{boletos_sin_venta} boleto(s) parseado(s) sin venta asociada',
                'severidad': 'warning' if boletos_sin_venta > 0 else 'info'
            },
            {
                'tipo': 'liquidaciones_vencidas',
                'count': liquidaciones_vencidas,
                'mensaje': f'{liquidaciones_vencidas} liquidación(es) pendiente(s) > 30 días',
                'severidad': 'error' if liquidaciones_vencidas > 0 else 'info'
            }
        ]
    })
