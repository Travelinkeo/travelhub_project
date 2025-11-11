"""
Sistema de búsqueda inteligente de boletos
"""
from django.db.models import Q
from core.models.boletos import BoletoImportado


def buscar_boletos_avanzado(
    nombre_pasajero=None,
    fecha_inicio=None,
    fecha_fin=None,
    origen=None,
    destino=None,
    aerolinea=None,
    estado=None,
    pnr=None
):
    """
    Búsqueda avanzada de boletos con múltiples filtros
    """
    queryset = BoletoImportado.objects.all()
    
    # Filtro por nombre (búsqueda parcial)
    if nombre_pasajero:
        queryset = queryset.filter(
            Q(nombre_pasajero_procesado__icontains=nombre_pasajero) |
            Q(nombre_pasajero_completo__icontains=nombre_pasajero)
        )
    
    # Filtro por rango de fechas
    if fecha_inicio and fecha_fin:
        queryset = queryset.filter(
            fecha_emision_boleto__range=[fecha_inicio, fecha_fin]
        )
    elif fecha_inicio:
        queryset = queryset.filter(fecha_emision_boleto__gte=fecha_inicio)
    elif fecha_fin:
        queryset = queryset.filter(fecha_emision_boleto__lte=fecha_fin)
    
    # Filtro por ruta (origen-destino)
    if origen or destino:
        ruta_query = Q()
        if origen:
            ruta_query &= Q(ruta_vuelo__icontains=origen)
        if destino:
            ruta_query &= Q(ruta_vuelo__icontains=destino)
        queryset = queryset.filter(ruta_query)
    
    # Filtro por aerolínea
    if aerolinea:
        queryset = queryset.filter(aerolinea_emisora__icontains=aerolinea)
    
    # Filtro por estado
    if estado:
        queryset = queryset.filter(estado_parseo=estado)
    
    # Filtro por PNR
    if pnr:
        queryset = queryset.filter(localizador_pnr__icontains=pnr)
    
    return queryset.select_related('venta_asociada').order_by('-fecha_emision_boleto')
