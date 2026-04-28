# contabilidad/views_tasas.py
"""
API endpoints para tasas de cambio de Venezuela
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.utils import timezone

from .tasas_venezuela_client import TasasVenezuelaClient
from .models import TasaCambioBCV
from datetime import date, datetime, timedelta


@api_view(['GET'])
@permission_classes([AllowAny])  # Público para mostrar en header
def obtener_tasas_actuales(request):
    """
    Obtiene las tasas actuales de cambio (BCV, Promedio, P2P).
    Auto-actualiza si han pasado más de 30 minutos desde última actualización.
    """
    cache_key = 'tasas_venezuela_actuales'
    cache_timestamp_key = 'tasas_venezuela_timestamp'
    
    # Verificar si necesita actualización (4 horas = 6 veces al día)
    last_update = cache.get(cache_timestamp_key)
    needs_update = not last_update or (datetime.now() - last_update) > timedelta(hours=4)
    
    if needs_update:
        # Actualizar tasas en background
        tasas = TasasVenezuelaClient.obtener_resumen_tasas()
        if tasas:
            cache.set(cache_key, tasas, 86400)  # 24 horas
            cache.set(cache_timestamp_key, datetime.now(), 86400)
    
    # Obtener del caché
    tasas_cached = cache.get(cache_key)
    
    if tasas_cached:
        return Response(tasas_cached)
    
    # Fallback a DB
    try:
        tasa_bcv_db = TasaCambioBCV.objects.filter(fecha=date.today()).first()
        if tasa_bcv_db:
            tasas = {
                'bcv': {
                    'valor': float(tasa_bcv_db.tasa_bsd_por_usd),
                    'fecha': tasa_bcv_db.fecha.strftime('%Y-%m-%d'),
                    'nombre': 'BCV Oficial (DB)'
                }
            }
            cache.set(cache_key, tasas, 86400)
            return Response(tasas)
    except Exception:
        pass
    
    return Response(
        {'error': 'No se pudieron obtener las tasas'},
        status=status.HTTP_503_SERVICE_UNAVAILABLE
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_tasa_bcv_simple(request):
    """
    Obtiene solo la tasa BCV oficial (simplificado para header).
    
    GET /api/contabilidad/tasas/bcv/
    
    Response:
    {
        "valor": 36.50,
        "fecha": "2025-01-20"
    }
    """
    cache_key = 'tasa_bcv_simple'
    tasa_cached = cache.get(cache_key)
    
    if tasa_cached:
        return Response(tasa_cached)
    
    # Intentar API primero
    tasa_api = TasasVenezuelaClient.obtener_tasa_bcv()
    
    if tasa_api:
        resultado = {
            'valor': float(tasa_api),
            'fecha': date.today().strftime('%Y-%m-%d')
        }
    else:
        # Fallback a DB
        try:
            tasa_db = TasaCambioBCV.objects.filter(fecha=date.today()).first()
            if not tasa_db:
                tasa_db = TasaCambioBCV.objects.latest('fecha')
            
            resultado = {
                'valor': float(tasa_db.tasa_bsd_por_usd),
                'fecha': tasa_db.fecha.strftime('%Y-%m-%d')
            }
        except TasaCambioBCV.DoesNotExist:
            return Response(
                {'error': 'No hay tasas disponibles'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Caché por 5 minutos
    cache.set(cache_key, resultado, 300)
    
    return Response(resultado)


@api_view(['POST'])
def sincronizar_tasas_manual(request):
    """
    Sincroniza las tasas manualmente (requiere autenticación).
    
    POST /api/contabilidad/tasas/sincronizar/
    """
    try:
        resultados = TasasVenezuelaClient.actualizar_tasas_db()
        
        # Limpiar caché
        cache.delete('tasas_venezuela_actuales')
        cache.delete('tasa_bcv_simple')
        
        return Response({
            'success': True,
            'resultados': resultados,
            'mensaje': 'Tasas sincronizadas correctamente'
        })
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
