# core/views/boleto_api_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
import logging

from apps.bookings.models import BoletoImportado, Venta, ItemVenta, SolicitudAnulacion
from core.serializers import BoletoImportadoSerializer
from core.security import get_agencia_from_request, get_object_tenant_or_404, filter_queryset_by_tenant, agency_role_required

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def boletos_sin_venta(request):
    """Lista de boletos parseados sin venta asociada. 🔐 Filtrado por agencia."""
    agencia = get_agencia_from_request(request)
    boletos = BoletoImportado.objects.filter(
        estado_parseo='COM',
        venta_asociada__isnull=True
    )
    boletos = filter_queryset_by_tenant(boletos, agencia).order_by('-fecha_subida')
    serializer = BoletoImportadoSerializer(boletos, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reintentar_parseo(request, boleto_id):
    """Reintentar parseo de un boleto. 🔐 Candado de agencia."""
    agencia = get_agencia_from_request(request)
    boleto = get_object_tenant_or_404(BoletoImportado, agencia, pk=boleto_id)

    boleto.estado_parseo = BoletoImportado.EstadoParseo.PENDIENTE
    boleto.log_parseo = "Reintentando parseo manualmente..."
    boleto.save()
    return Response({'status': 'Parseo reiniciado', 'boleto_id': boleto.id_boleto_importado})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_venta_desde_boleto(request, boleto_id):
    """Crear venta automáticamente desde un boleto parseado. 🔐 Candado de agencia."""
    agencia = get_agencia_from_request(request)
    boleto = get_object_tenant_or_404(BoletoImportado, agencia, pk=boleto_id)

    if boleto.estado_parseo != 'COM':
        return Response({'error': 'El boleto debe estar parseado correctamente'}, status=status.HTTP_400_BAD_REQUEST)
    
    if boleto.venta_asociada:
        return Response({'error': 'El boleto ya tiene una venta asociada'}, status=status.HTTP_400_BAD_REQUEST)
    
    from core.models_catalogos import Moneda, ProductoServicio
    moneda_usd, _ = Moneda.objects.get_or_create(codigo_iso='USD', defaults={'nombre': 'Dólar Estadounidense'})
    
    venta = Venta.objects.create(
        moneda=moneda_usd,
        subtotal=boleto.tarifa_base or 0,
        impuestos=boleto.impuestos_total_calculado or 0,
        descripcion_general=f"Venta desde Boleto Nro: {boleto.numero_boleto} para {boleto.nombre_pasajero_completo}",
        creado_por=request.user,
        agencia=boleto.agencia
    )
    
    producto_aereo, _ = ProductoServicio.objects.get_or_create(tipo_producto='AIR', defaults={'nombre': 'Boleto Aéreo Genérico'})
    
    ItemVenta.objects.create(
        venta=venta,
        producto_servicio=producto_aereo,
        cantidad=1,
        precio_unitario_venta=boleto.total_boleto or 0,
        descripcion_personalizada=f"Boleto: {boleto.numero_boleto}, Ruta: {boleto.ruta_vuelo.replace('\n', ' ') if boleto.ruta_vuelo else ''}",
        codigo_reserva_proveedor=boleto.localizador_pnr
    )
    
    boleto.venta_asociada = venta
    boleto.save()
    
    return Response({
        'status': 'Venta creada exitosamente',
        'venta_id': venta.id_venta,
        'localizador': venta.localizador
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Métricas para el dashboard de boletos"""
    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)
    
    if request.user.is_superuser:
        boletos_qs = BoletoImportado.objects.all()
    elif hasattr(request.user, 'agencias'):
        ua = request.user.agencias.filter(activo=True).first()
        if ua:
            boletos_qs = BoletoImportado.objects.filter(agencia=ua.agencia)
        else:
            boletos_qs = BoletoImportado.objects.none()
    else:
        boletos_qs = BoletoImportado.objects.none()

    procesados_hoy = boletos_qs.filter(fecha_subida__date=hoy, estado_parseo='COM').count()
    procesados_semana = boletos_qs.filter(fecha_subida__date__gte=inicio_semana, estado_parseo='COM').count()
    procesados_mes = boletos_qs.filter(fecha_subida__date__gte=inicio_mes, estado_parseo='COM').count()
    
    pendientes = boletos_qs.filter(estado_parseo='PEN').count()
    errores = boletos_qs.filter(estado_parseo='ERR').count()
    
    top_aerolineas = list(boletos_qs.filter(
        fecha_subida__date__gte=inicio_mes,
        estado_parseo='COM'
    ).values('aerolinea_emisora').annotate(
        cantidad=Count('id_boleto_importado')
    ).order_by('-cantidad')[:5])
    
    return Response({
        'procesados': {'hoy': procesados_hoy, 'semana': procesados_semana, 'mes': procesados_mes},
        'pendientes': pendientes,
        'errores': errores,
        'top_aerolineas': top_aerolineas
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def buscar(request):
    """Búsqueda avanzada de boletos"""
    if request.user.is_superuser:
        qs = BoletoImportado.objects.all()
    elif hasattr(request.user, 'agencias'):
        ua = request.user.agencias.filter(activo=True).first()
        if ua:
            # Fix: Or query to include orphan boletos if we want everyone to see them, 
            # but usually they belong to an agency. For now, strict filter.
            qs = BoletoImportado.objects.filter(agencia=ua.agencia)
        else:
            return Response([])
    else:
        return Response([])

    nombre = request.GET.get('nombre')
    pnr = request.GET.get('pnr')
    origen = request.GET.get('origen')
    destino = request.GET.get('destino')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if nombre:
        qs = qs.filter(Q(nombre_pasajero_completo__icontains=nombre) | Q(nombre_pasajero_procesado__icontains=nombre))
    if pnr:
        qs = qs.filter(localizador_pnr__icontains=pnr)
    if origen:
        qs = qs.filter(ruta_vuelo__icontains=origen)
    if destino:
        qs = qs.filter(ruta_vuelo__icontains=destino)
    if fecha_inicio:
        qs = qs.filter(fecha_emision_boleto__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha_emision_boleto__lte=fecha_fin)
        
    qs = qs.order_by('-fecha_emision_boleto')[:50]
    serializer = BoletoImportadoSerializer(qs, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reporte_comisiones(request):
    """Reporte de comisiones por aerolínea"""
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if request.user.is_superuser:
        qs = BoletoImportado.objects.all()
    elif hasattr(request.user, 'agencias'):
        ua = request.user.agencias.filter(activo=True).first()
        if ua:
            qs = BoletoImportado.objects.filter(agencia=ua.agencia)
        else:
            return Response({'totales': {}, 'por_aerolinea': []})
    else:
        return Response({'totales': {}, 'por_aerolinea': []})
        
    if fecha_inicio:
        qs = qs.filter(fecha_emision_boleto__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha_emision_boleto__lte=fecha_fin)
        
    qs = qs.filter(estado_parseo='COM')
    
    totales = qs.aggregate(
        total_boletos=Count('id_boleto_importado'),
        total_ventas=Sum('total_boleto'),
        total_comisiones=Sum('comision_agencia')
    )
    
    por_aerolinea = qs.values('aerolinea_emisora').annotate(
        cantidad_boletos=Count('id_boleto_importado'),
        total_ventas=Sum('total_boleto'),
        total_comisiones=Sum('comision_agencia')
    ).order_by('-total_comisiones')
    
    return Response({
        'totales': {
            'total_boletos': totales['total_boletos'] or 0,
            'total_ventas': totales['total_ventas'] or 0,
            'total_comisiones': totales['total_comisiones'] or 0
        },
        'por_aerolinea': [
            {
                'aerolinea': item['aerolinea_emisora'] or 'Desconocida',
                'cantidad_boletos': item['cantidad_boletos'],
                'total_ventas': item['total_ventas'] or 0,
                'total_comisiones': item['total_comisiones'] or 0
            }
            for item in por_aerolinea
        ]
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def solicitar_anulacion(request):
    """Crear solicitud de anulación. 🔐 Candado de agencia."""
    data = request.data
    boleto_id = data.get('boleto')
    agencia = get_agencia_from_request(request)
    boleto = get_object_tenant_or_404(BoletoImportado, agencia, pk=boleto_id)

    try:
        monto_original = float(data.get('monto_original', 0))
        penalidad = float(data.get('penalidad_aerolinea', 0))
        fee = float(data.get('fee_agencia', 0))
        
        solicitud = SolicitudAnulacion.objects.create(
            boleto=boleto,
            tipo=data.get('tipo_anulacion'),
            motivo=data.get('motivo'),
            monto_original=monto_original,
            penalidad_aerolinea=penalidad,
            fee_agencia=fee,
            usuario_solicitante=request.user
        )
        return Response({'id_anulacion': solicitud.id, 'monto_reembolso': solicitud.monto_reembolso})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detalle_boleto(request, boleto_id):
    """Obtener detalle de un boleto. 🔐 Candado de agencia."""
    agencia = get_agencia_from_request(request)
    boleto = get_object_tenant_or_404(BoletoImportado, agencia, pk=boleto_id)
                 
    data = {
        'numero_boleto': boleto.numero_boleto,
        'localizador_pnr': boleto.localizador_pnr,
        'nombre_pasajero_procesado': boleto.nombre_pasajero_procesado,
        'aerolinea_emisora': boleto.aerolinea_emisora,
        'fecha_emision': boleto.fecha_emision_boleto,
        'total_boleto': boleto.total_boleto,
        'ruta': boleto.ruta_vuelo,
        'archivo_pdf': boleto.archivo_pdf_generado.url if boleto.archivo_pdf_generado else (boleto.archivo_boleto.url if boleto.archivo_boleto else None)
    }
    return Response(data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@agency_role_required(['admin', 'gerente']) # 🔐 Solo gerentes o admins pueden borrar boletos importados
def eliminar_boleto(request, boleto_id):
    """Eliminar un boleto importado. 🔐 Candado de agencia."""
    agencia = get_agencia_from_request(request)
    boleto = get_object_tenant_or_404(BoletoImportado, agencia, pk=boleto_id)
    boleto.delete()
    return Response({'status': 'deleted'})
