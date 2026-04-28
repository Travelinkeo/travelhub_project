# core/views/dashboard_views.py
import logging
from datetime import timedelta
from decimal import Decimal
from django.db.models import Count, Sum
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import render
from django.views.generic import View

from core.models import LiquidacionProveedor, TasaCambio
from apps.bookings.models import Venta, BoletoImportado, ItemVenta
from apps.finance.models import Factura
from apps.crm.models import OportunidadViaje
from core.models_catalogos import TipoCambio, Moneda
from core.throttling import DashboardRateThrottle
from core.cache import cache_api_response

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([DashboardRateThrottle])
@cache_api_response(timeout=300, key_prefix='dashboard')
def dashboard_metricas(request):
    fecha_desde = request.GET.get('fecha_desde')
    fecha_hasta = request.GET.get('fecha_hasta')
    
    ua = request.user.agencias.filter(activo=True).first()
    agencia = ua.agencia if ua else None
    
    if not agencia:
        return Response({'resumen': {}, 'error': 'No agency found'}, status=403)

    ventas_qs = Venta.objects.filter(agencia=agencia)
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
    ua = request.user.agencias.filter(activo=True).first()
    agencia = ua.agencia if ua else None
    
    if not agencia:
        return Response({'alertas': []}, status=403)

    ventas_sin_cliente = Venta.objects.filter(agencia=agencia, cliente__isnull=True).count()
    
    hace_7_dias = timezone.now() - timedelta(days=7)
    ventas_mora = Venta.objects.filter(
        agencia=agencia,
        saldo_pendiente__gt=0,
        fecha_venta__lt=hace_7_dias
    ).count()
    
    boletos_sin_venta = BoletoImportado.objects.filter(
        agencia=agencia,
        estado_parseo='COM',
        venta_asociada__isnull=True
    ).count()
    
    hace_30_dias = timezone.now() - timedelta(days=30)
    liquidaciones_vencidas = LiquidacionProveedor.objects.filter(
        agencia=agencia,
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
                'severidad': 'warning' if ventas_mora > 0 else 'info'
            },
            {
                'tipo': 'boletos_sin_venta',
                'count': boletos_sin_venta,
                'mensaje': f'{boletos_sin_venta} boleto(s) sin venta asociada',
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


class DashboardView(LoginRequiredMixin, View):
    def get_vendedor_dashboard(self, request, agencia):
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)
        
        # Stats personales del mes (blindadas por agencia)
        base_qs_ventas = Venta.objects.filter(agencia=agencia, creado_por=request.user, fecha_venta__gte=inicio_mes)
        boletos_mes = BoletoImportado.objects.filter(
            agencia=agencia,
            venta_asociada__creado_por=request.user, 
            fecha_subida__gte=inicio_mes
        ).count()
        
        monto_total_mes = base_qs_ventas.aggregate(total=Sum('total_venta'))['total'] or 0
        comisiones_mes = ItemVenta.objects.filter(
            agencia=agencia,
            venta__creado_por=request.user, 
            venta__fecha_venta__gte=inicio_mes
        ).aggregate(total=Sum('comision_agencia_monto'))['total'] or 0
        
        # Meta personalizada
        meta_monto = 20000
        porcentaje_meta = min(int((monto_total_mes / meta_monto) * 100), 100) if meta_monto > 0 else 0
        
        # Leads Calientes (Exclusivos del vendedor y su agencia)
        leads_calientes = OportunidadViaje.objects.filter(
            agencia=agencia,
            etapa__in=['NEW', 'QUO', 'PAY']
        ).select_related('cliente').order_by('-actualizado_en')[:5]
        
        # Ventas Recientes para el Feed/Timeline
        ventas_recientes = Venta.objects.filter(
            agencia=agencia,
            creado_por=request.user
        ).select_related('cliente', 'moneda').prefetch_related('boletos_adjuntos').order_by('-fecha_venta')[:8]

        context = {
            'stats': {
                'boletos_mes': boletos_mes,
                'monto_mes': monto_total_mes,
                'comisiones_mes': comisiones_mes,
                'porcentaje_meta': porcentaje_meta,
                'meta_monto': meta_monto,
                'leads_count': leads_calientes.count()
            },
            'leads_calientes': leads_calientes,
            'ventas_recientes': ventas_recientes,
            'agencia': agencia,
            'hoy': hoy
        }
        # Renderiza con namespace completo por exigencia arquitectónica de la nube
        return render(request, 'core/dashboard_asesor.html', context)

    def get(self, request):
        # 1. Detección de Agencia Activa (Multi-tenant)
        ua = request.user.agencias.filter(activo=True).first()
        agencia = ua.agencia if ua else None
        
        if not agencia:
             return render(request, 'errors/no_agency.html', {
                 'message': "No tienes una agencia activa asociada a tu cuenta."
             })

        rol = ua.rol if ua else None
        if rol == 'vendedor':
            return self.get_vendedor_dashboard(request, agencia)

        # 2. CALCULO DE STATS CON NUEVO MOTOR BLINDADO
        from core.dashboard_stats import get_dashboard_stats
        stats = get_dashboard_stats(agencia)

        # 3. TASAS (CON FALLBACK ANTI-CEROS)
        tasa_usd_obj = TasaCambio.objects.filter(moneda='USD').order_by('-fecha').first()
        tasas = {
            'USD': "{:,.2f}".format(tasa_usd_obj.monto) if tasa_usd_obj else "473.87",
        }
            
        # 4. TABLA RECIENTE (Limitada a agencia)
        ventas_recientes = Venta.objects.filter(agencia=agencia).select_related('cliente', 'moneda').order_by('-fecha_venta')[:8]

        # 5. ALERTAS (Ya blindadas en stats o calculadas aquí)
        alertas = {
            'sin_cliente': Venta.objects.filter(agencia=agencia, cliente__isnull=True).count(),
            'deuda_antigua': Venta.objects.filter(agencia=agencia, saldo_pendiente__gt=0, fecha_venta__lt=(timezone.now() - timedelta(days=7))).count(),
            'boletos_huerfanos': BoletoImportado.objects.filter(agencia=agencia, venta_asociada__isnull=True).count()
        }

        # Tasas de cambio para el sidebar
        tasas_sidebar = TipoCambio.objects.filter(moneda_destino__codigo_iso='VES').order_by('-fecha_efectiva')[:3]

        context = {
            'agencia': agencia,
            'tasas': tasas_sidebar,
            'stats': stats, # Contiene automatización, margen, etc.
            'ganancia_estimada': stats.get('ventas_mes', {}).get('total', 0), # Para retrocompatibilidad manual
            'saldo_pendiente': stats.get('pendientes_pago', {}).get('total', 0),
            'ventas_recientes': ventas_recientes,
            'alertas': alertas,
            'hoy': timezone.now()
        }
        
        return render(request, 'core/dashboard_modern.html', context)
        
        # Renderiza con namespace completo por exigencia arquitectónica de la nube
        return render(request, 'core/dashboard_modern.html', context)