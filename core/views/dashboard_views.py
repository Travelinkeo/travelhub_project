# core/views/dashboard_views.py
from datetime import timedelta
from django.db.models import Count, Sum
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Venta, LiquidacionProveedor, BoletoImportado
from apps.finance.models import Factura
from core.models_catalogos import TipoCambio, Moneda
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

from django.shortcuts import render

from django.views.generic import TemplateView
from django.db.models import Sum, Q, Count

from django.shortcuts import render
from django.views.generic import View
from django.db.models import Sum
from django.utils import timezone
from core.models import ItemVenta, Venta, BoletoImportado
from core.models_catalogos import TipoCambio, Moneda

class DashboardView(View):
    def get(self, request):
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)

        # 1. TASAS (Manejo de errores robusto con campos correctos)
        tasas = {'USD': 0, 'EUR': 0}
        # 1. TASAS (SIN SILENCIADOR PARA VER EL ERROR)
        tasas = {'USD': 0, 'EUR': 0}
        
        # Buscamos moneda local para referencia
        moneda_local = Moneda.objects.filter(es_moneda_local=True).first()
        
        # Helper interno para buscar tasa
        def get_tasa(iso_origen, moneda_dest):
            qs = TipoCambio.objects.filter(moneda_origen__codigo_iso=iso_origen)
            if moneda_dest:
                qs = qs.filter(moneda_destino=moneda_dest)
            return qs.order_by('-fecha_efectiva', '-id_tipo_cambio').first()

        if moneda_local:
             usd_obj = get_tasa('USD', moneda_local)
        else:
             usd_obj = None
        
        # Fallback/Priority Override: Verifica explícitamente VES, ya que es la moneda de curso legal actual
        # y a menudo moneda_local se queda como VED en sistemas legacy.
        ves_moneda = Moneda.objects.filter(codigo_iso='VES').first()
        if ves_moneda:
            usd_ves_obj = get_tasa('USD', ves_moneda)
            # Si encontramos tasa VES y es más reciente o igual que la local (o si la local no existía), usamos VES
            if usd_ves_obj:
                if not usd_obj or (usd_ves_obj.fecha_efectiva >= usd_obj.fecha_efectiva):
                    usd_obj = usd_ves_obj

        if usd_obj:
            # Formatear a 2 decimales para evitar problemas de renderizado en template
            tasas['USD'] = "{:,.2f}".format(usd_obj.tasa_conversion)

        # EUR
        eur_obj = None
        if moneda_local:
            eur_obj = get_tasa('EUR', moneda_local)
        
        # Check VES explicitly (like we did for USD)
        if ves_moneda:
            eur_ves_obj = get_tasa('EUR', ves_moneda)
            if eur_ves_obj:
                # Use VES if we didn't find a local rate OR if VES rate is newer
                if not eur_obj or (eur_ves_obj.fecha_efectiva >= eur_obj.fecha_efectiva):
                    eur_obj = eur_ves_obj

        if eur_obj:
             # Formatear a 2 decimales
            tasas['EUR'] = "{:,.2f}".format(eur_obj.tasa_conversion)
            
            
        # 2. FINANZAS
        # Filtramos ventas del mes
        items_mes = ItemVenta.objects.filter(venta__fecha_venta__gte=inicio_mes)
        ganancia = items_mes.aggregate(t=Sum('comision_agencia_monto'))['t'] or 0
        deuda = items_mes.aggregate(t=Sum('costo_neto_proveedor'))['t'] or 0

        # 3. TABLA RECIENTE
        ventas_recientes = Venta.objects.select_related('cliente').order_by('-fecha_venta')[:5]

        # 4. ALERTAS
        hace_7_dias = hoy - timezone.timedelta(days=7)
        alertas = {
            'sin_cliente': Venta.objects.filter(cliente__isnull=True).count(),
            'deuda_antigua': Venta.objects.filter(saldo_pendiente__gt=0, fecha_venta__lt=hace_7_dias).count(),
            'boletos_huerfanos': BoletoImportado.objects.filter(venta_asociada__isnull=True).count()
        }

        context = {
            'tasas': tasas,
            'ganancia_estimada': ganancia,
            'saldo_pendiente': deuda,
            'ventas_recientes': ventas_recientes,
            'alertas': alertas,
            'hoy': hoy
        }
        
        # IMPORTANTE: Conectamos con el archivo HTML actualizado
        return render(request, 'dashboard_modern.html', context)

