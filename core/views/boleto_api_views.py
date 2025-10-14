# core/views/boleto_api_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from core.models import BoletoImportado, Venta
from core.serializers import BoletoImportadoSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def boletos_sin_venta(request):
    """Lista de boletos parseados sin venta asociada"""
    boletos = BoletoImportado.objects.filter(
        estado_parseo='COM',
        venta_asociada__isnull=True
    ).order_by('-fecha_subida')
    
    serializer = BoletoImportadoSerializer(boletos, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reintentar_parseo(request, boleto_id):
    """Reintentar parseo de un boleto"""
    boleto = get_object_or_404(BoletoImportado, pk=boleto_id)
    
    boleto.estado_parseo = BoletoImportado.EstadoParseo.PENDIENTE
    boleto.log_parseo = "Reintentando parseo manualmente..."
    boleto.save()
    
    return Response({
        'status': 'Parseo reiniciado',
        'boleto_id': boleto.id_boleto_importado
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_venta_desde_boleto(request, boleto_id):
    """Crear venta automáticamente desde un boleto parseado"""
    boleto = get_object_or_404(BoletoImportado, pk=boleto_id)
    
    if boleto.estado_parseo != 'COM':
        return Response(
            {'error': 'El boleto debe estar parseado correctamente'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if boleto.venta_asociada:
        return Response(
            {'error': 'El boleto ya tiene una venta asociada'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Crear venta básica
    from core.models_catalogos import Moneda, ProductoServicio
    
    moneda_usd, _ = Moneda.objects.get_or_create(
        codigo_iso='USD',
        defaults={'nombre': 'Dólar Estadounidense'}
    )
    
    venta = Venta.objects.create(
        moneda=moneda_usd,
        subtotal=boleto.tarifa_base or 0,
        impuestos=boleto.impuestos_total_calculado or 0,
        descripcion_general=f"Venta desde Boleto Nro: {boleto.numero_boleto} para {boleto.nombre_pasajero_completo}",
        creado_por=request.user
    )
    
    # Crear item de venta
    producto_aereo, _ = ProductoServicio.objects.get_or_create(
        tipo_producto='AIR',
        defaults={'nombre': 'Boleto Aéreo Genérico'}
    )
    
    from core.models import ItemVenta
    ItemVenta.objects.create(
        venta=venta,
        producto_servicio=producto_aereo,
        cantidad=1,
        precio_unitario_venta=boleto.total_boleto or 0,
        descripcion_personalizada=f"Boleto: {boleto.numero_boleto}, Ruta: {boleto.ruta_vuelo.replace(chr(10), ' ') if boleto.ruta_vuelo else ''}",
        codigo_reserva_proveedor=boleto.localizador_pnr
    )
    
    # Asociar boleto con venta
    boleto.venta_asociada = venta
    boleto.save()
    
    return Response({
        'status': 'Venta creada exitosamente',
        'venta_id': venta.id_venta,
        'localizador': venta.localizador
    }, status=status.HTTP_201_CREATED)
